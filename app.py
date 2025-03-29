from flask import Flask, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import time
import threading
import requests
from requests.auth import HTTPBasicAuth
from xml.etree import ElementTree as ET
from functools import wraps
from dotenv import load_dotenv
import os


load_dotenv()

app = Flask(__name__)

# Configuration
MAX_RETRIES = 3
RETRY_DELAY = 3  # seconds
SCORING_TIMEOUT = 30  # seconds
LOAN_PROCESSING_TIME = (10, 30)  # Min/max seconds

# In-memory stores
active_subscriptions = {}
loan_applications = {}
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
users = {
    USERNAME: generate_password_hash(PASSWORD)
}

# Mock SOAP and Scoring Service Config
SOAP_KYC_URL = os.getenv('SOAP_KYC_URL')           # http://localhost:8093
SCORING_URL = os.getenv('SCORING_URL')             # http://localhost:8095
SOAP_USER = os.getenv('SOAP_USER')
SOAP_PASS = os.getenv('SOAP_PASS')

# Authentication decorator
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_credentials(auth.username, auth.password):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)

    return decorated


def check_credentials(username, password):
    return username in users and check_password_hash(users[username], password)


def get_kyc_data(customer_number):
    """Query SOAP KYC endpoint"""
    soap_request = f"""<?xml version="1.0"?>
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
                      xmlns:cust="http://credable.io/cbs/customer">
       <soapenv:Header/>
       <soapenv:Body>
          <cust:CustomerRequest>
             <cust:customerNumber>{customer_number}</cust:customerNumber>
          </cust:CustomerRequest>
       </soapenv:Body>
    </soapenv:Envelope>"""

    response = requests.post(
        f'{SOAP_KYC_URL}/service/customer',
        data=soap_request,
        headers={'Content-Type': 'text/xml'},
        auth=HTTPBasicAuth(SOAP_USER, SOAP_PASS)
    )

    if response.status_code != 200:
        return None

    ns = {'tns': 'http://credable.io/cbs/customer'}
    root = ET.fromstring(response.text)
    customer = root.find('.//tns:customer', ns)

    return {
        'customerNumber': customer.findtext('tns:customerNumber', '', ns),
        'status': customer.findtext('tns:status', '', ns),
        'monthlyIncome': float(customer.findtext('tns:monthlyIncome', '0', ns))
    }


def get_customer_score(customer_number, retries=MAX_RETRIES):
    """Query scoring engine with retry logic"""
    # Initiate scoring
    scoring_response = requests.get(
        f'{SCORING_URL}/api/v1/scoring/initiateQueryScore/{customer_number}',
        auth=HTTPBasicAuth(SOAP_USER, SOAP_PASS)
    )

    if scoring_response.status_code != 200:
        return None

    scoring_token = scoring_response.json().get('token')

    # Check score with retries
    for _ in range(retries):
        check_response = requests.get(
            f"{SCORING_URL}/api/v1/scoring/queryScore/{scoring_token}",
            auth=HTTPBasicAuth(SOAP_USER, SOAP_PASS)
        )

        if check_response.status_code == 200:
            data = check_response.json()
            return data['score']
        else:
            time.sleep(RETRY_DELAY)
            continue

    return None


def process_loan_application(application_id):
    """Background loan processing"""
    application = loan_applications[application_id]
    customer_number = application['customer_number']
    amount = application['amount']

    try:
        # Step 1: Get KYC data
        kyc_data = get_kyc_data(customer_number)
        if not kyc_data or kyc_data['status'] != 'ACTIVE':
            loan_applications[application_id]['status'] = 'REJECTED'
            loan_applications[application_id]['reason'] = 'KYC check failed'
            return

        # Step 2: Get credit score
        score = get_customer_score(customer_number)
        if not score:
            loan_applications[application_id]['status'] = 'REJECTED'
            loan_applications[application_id]['reason'] = 'Scoring service unavailable'
            return

        # Step 3: Decision logic
        """ 
        LMS can use LoanLimit to reject applications above the limit or combination of score and limit,
        But I have used monthlyIncome to limit how much customer can apply.
        """
        max_loan = kyc_data['monthlyIncome'] * 0.5  # 50% of monthly income
        if score >= 700 and amount <= max_loan:
            status = 'APPROVED'
        elif score >= 400 and amount <= max_loan:
            status = 'APPROVED'
        else:
            status = 'REJECTED'

        loan_applications[application_id].update({
            'status': status,
            'score': score,
            'kyc_data': kyc_data,
            'processed_at': time.time()
        })

    except Exception as e:
        loan_applications[application_id]['status'] = 'FAILED'
        loan_applications[application_id]['reason'] = str(e)


# --- API Endpoints ---
@app.route('/api/v1/subscribe', methods=['POST'])
@requires_auth
def subscribe_customer():
    """Subscribe a customer for loan services"""
    data = request.get_json()
    customer_number = data.get('customer_number')

    if not customer_number:
        return jsonify({"error": "customer_number is required"}), 400

    if customer_number in active_subscriptions:
        return jsonify({"error": "Customer already subscribed"}), 400

    subscription_id = str(uuid.uuid4())
    active_subscriptions[customer_number] = {
        'subscription_id': subscription_id,
        'created_at': time.time(),
        'active_loan': None
    }

    return jsonify({
        "subscription_id": subscription_id,
        "status": "active"
    })


@app.route('/api/v1/request-loan', methods=['POST'])
@requires_auth
def request_loan():
    """Submit a new loan application"""
    data = request.get_json()
    customer_number = data.get('customer_number')
    amount = float(data.get('amount', 0))

    # Validation
    if not customer_number or amount <= 0:
        return jsonify({"error": "Valid customer_number and amount required"}), 400

    if customer_number not in active_subscriptions:
        return jsonify({"error": "Customer not subscribed"}), 400

    if active_subscriptions[customer_number]['active_loan']:
        return jsonify({"error": "Loan already in progress"}), 400

    # Create loan application
    application_id = str(uuid.uuid4())
    loan_applications[application_id] = {
        'customer_number': customer_number,
        'amount': amount,
        'status': 'PROCESSING',
        'created_at': time.time()
    }

    # Mark customer as having active loan
    active_subscriptions[customer_number]['active_loan'] = application_id

    # Start background processing
    threading.Thread(
        target=process_loan_application,
        args=(application_id,)
    ).start()

    return jsonify({
        "application_id": application_id,
        "status": "PROCESSING"
    })


@app.route('/api/v1/loan-status/<application_id>', methods=['GET'])
@requires_auth
def loan_status(application_id):
    """Check loan application status"""
    try:
        application = loan_applications[application_id]
        response = {
            "application_id": application_id,
            "status": application['status'],
            "customer_number": application['customer_number'],
            "amount": application['amount']
        }
        if application['status'] in ['APPROVED', 'REJECTED', 'FAILED']:
            response.update({
                "processed_at": application.get('processed_at'),
                "reason": application.get('reason'),
                "score": application.get('score')
            })

            # Clean up active loan flag if completed
            customer_number = application['customer_number']
            if customer_number in active_subscriptions:
                active_subscriptions[customer_number]['active_loan'] = None

        return jsonify(response)
    except KeyError as e:
        return jsonify({"error": f"Application ID: {e.args[0]} not found"}), 404


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "active_subscriptions": len(active_subscriptions),
        "active_loans": sum(1 for app in loan_applications.values()
                            if app['status'] == 'PROCESSING')
    })


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'


if __name__ == '__main__':
    app.run()

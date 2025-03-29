# Loan Management Service
This is a simple Loan Management Module (LMS) which will be integrated to the Bank's CORE Banking system [(CBS)](https://github.com/patrickRobotics/cbs) 
and the [Scoring Engine](https://github.com/patrickRobotics/scoring-engine) to extend micro loan products to the Bank customers. 
The Lending Platform wil extend APIs to the Mobile Application, query the Scoring Engine, and consume data from the CORE Banking System, here, 
via a [middleware service](https://github.com/patrickRobotics/lms_middleware).

Customers will be accessing the lending product through a Bank Mobile Application. The CBS system exposes two SOAP APIS;
1. KYC API from which one is able to fetch customer information
2. Transactions Data API which on is able to fetch historical transactional records of the customer.

This LMS module exposes RESTful APIs to client Applications;
1. Subscription API. The Mobile Application will submit a Customer Number
2. Loan request API. The Mobile Application will submit a customer Number and an amount
3. Loan Status API. The Mobile Application will query for the loan status.

**Note:** Customers should not be able to apply for another loan if there is an ongoing loan request.

LMS can query the scoring engine to get the score and the limit before issuing a loan to the customer. Getting scoring and limits is a two steps process;
1. Initiate query score, which you submit a customer number and receive back a token (application_id)
2. Query score using the token/application_id from the previous step.

## Setup
Clone all 4 repositories related to this project:
- [Core Banking Service](https://github.com/patrickRobotics/cbs)
- [Scoring Service](https://github.com/patrickRobotics/scoring-engine)
- [Middleware Service](middleware service](https://github.com/patrickRobotics/lms_middleware)

Create a **.env** file to store secret variables for your environment and populate values for the keys listed below:
```
SOAP_KYC_URL=        # HOST URL for the main Customer KYC SOAP service, e.g. http://localhost:8001
SCORING_URL=         # HOST URL for the scoring-service, e.g. http://127.0.0.1:5001
SOAP_USER=admin      # user name used to authenticate on the Customer KYC Service
SOAP_PASS=pwd123     # password for the user above
USERNAME=            # username for basic authentication on this service
PASSWORD=            # password for basic auth on this service
```

## Create & Activate a Python virtualenvironment to install the needed dependencies.
`python3 -m venv .venv`

`source .venv/bin/activate`

## Insall project dependencies
`pip install -r requirements.txt`

## Start the service
`flask run --host=0.0.0.0 --port=8000`

## Test loan application APIs
This project has used one customer for testing: customer number **234774784**.

Before you can use the Loan Management Service, ensure the other services (**Scoring and KYC service**) are running and the HOST urls configured properly in the **.env** file.

a. Customer Subscribe: Send POST request to `http://127.0.0.1:<PORT>/api/v1/subscribe` providing payload; `{ "customer_number": 234774784 }`

b. Loan appliction: Send POST request to `http://127.0.0.1:5002/api/v1/request-loan` providing payload; `{ "customer_number": 234774784, "amount": 1000 }`
   Successful response will be as follows: 
   ```json 
   {
     "application_id": "f679c506-119e-4f09-94f5-0ad597cb03b1",
     "status": "PROCESSING"
   }
   ```
   Customer who has not yet subscribed response looks like:
   ```json
   {
       "error": "Customer not subscribed"
   }   
   ```
   Customer with another loan application in progress looks like:
   ```json
   {
       "error": "Loan already in progress"
   }
   ```

c. Check loan status: Send GET request to `http://127.0.0.1:5002/api/v1/loan-status/<application_id>`
   Loan approved response looks like:

   ```json
   {
     "amount": 1000.0,
     "application_id": "f679c506-119e-4f09-94f5-0ad597cb03b1",
     "customer_number": 234774784,
     "processed_at": 1743208194.9507303,
     "reason": null,
     "score": 508,
     "status": "APPROVED"
   }
   ```

   invalid application_id response looks like:
   ```json
   {
       "error": "Application ID: f679c506-119e-4f09-94f5-0ad597cb03b1 not found"
   }
   ```

   
A [Postman collection](https://galactic-crater-247223.postman.co/workspace/New-Team-Workspace~d654769e-41a2-41a1-b0b2-7e6cfdc6fbfa/collection/2496867-0b5a4eb2-ab77-4e42-8911-78cc232a4f36?action=share&creator=2496867) has been provided here for quick testing

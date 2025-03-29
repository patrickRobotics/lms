## Setup
1. Create a **.env** file to store secret variables for your environment and populate values for the keys listed below:
```
SOAP_KYC_URL=        # HOST URL for the main Customer KYC SOAP service, e.g. http://localhost:8001
SCORING_URL=         # HOST URL for the scoring-service, e.g. http://127.0.0.1:5001
SOAP_USER=admin      # user name used to authenticate on the Customer KYC Service
SOAP_PASS=pwd123     # password for the user above
```

2. ## Create a Python virtualenvironment to install the needed dependencies.
   `python3 -m venv .venv`
4. ## Insall project dependencies
   `pip install -r requirements.txt`
6. ## Start the service
   `flask run --host=0.0.0.0 --port=8000`
8. ## Test loan application APIs
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
   

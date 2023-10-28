<h1>Documentation for Backend API using Fast API</h1>

## Setting Up Environment

### Prerequisities : 
1. Python installed
2. Node.js installed

### Setting Up Python Libraries
- After you clone the project, just run
```
    pip install -r requirements.txt
```

### Setting Up React Frontend
- After you clone the project, run 
```
    cd client
    npm install
```

### Libraries used for processing Pdfs : 
- PdfPlumber :
    This library has been used to parse out the images from the pdfs.
- PyMuPdf :
    This library has been used to parse out the text from the pdfs as it has higher accuracy than PdfPlumber in that aspect.

## Structure of the project :

### main.py
- This is the main file of the backend where Fast Api server is defined and the routers paths have been defined and mounted on the application along with setting up serving of static files.

### client
- This is the folder containing the react frontend files. This folder contains following :
    - build folder :
        - This folder is generated after the react project is built using ```npm run build```
        - This folder contains final static files which are to be served by the server at "/" endpoint.
    - public folder :
        - This folder contains automatically generated files with create-react-app along with inde.html
    - src folder :
        - This folder contains index.js & app.js.
        - In App.js, we have created a page for "/" or "/index.html" endpoints to get user's gmail permissions.
        - When user clicks on the yes button on the page, call to authorise the app to access the user's gmail is created using credentials from google cloud console.
        - After user authorises the app or denies access to the app, user is redirected to "/" with code which makes get call on "/" endpoint to which server responds according to the response.

### error-templates
- This folder contains the html files :
    - access_denied.html : 
        - When the user denies the access to the application then server serves this file after the google auth redirects user to the redirect_uri.
    - link_expired.html :
        - After the app has got permissions once and user retries to send the get request on the server on same url with same code then this file is served.

### pdf_processing_controller
- This folder contains process_pdf.py which contains process_pdf_file function.
- After the email's data is decoded and found to be a pdf, then this function will be called with decoded pdf file data in the arguement which it will process using the pdfplumber , fitz (pymupdf) for images and text respectively.
- The images parsed by pdfplumber will be added to the attachments folder.

### attachments
- This folder will contain the images parsed by the pdfplumber in a pdf.

### models
- This directory contains users.py file.
- users.py is where the model to store users who have provided the access to the application will be stored.
- The database used is mysql.
- For connecting to database, Replace 'mysql+mysqlconnector://username:password@localhost/dbname' with your MySQL database URL.
- The user model has 3 attributes : 
    - email : To store the email address which has provided application access to gmail.
    - access_token  : To store the access token of the user received while permissions were granted by the user.
    - refresh_token : To store the refresh token of the user received while permissions were granted by the user.
- We need these 3 things so that we can get user's email's data on different endpoints.
- The functions are defined here to add, update or find a user.

### routers
- This directory contains api_router.py which will contain router to serve requests to api endpoints.
- API Endpoints :
    - "/api" : 
        - Get request on this endpoint is done after the user is redirected by google auth along with either code and scope query parameter or error query parameter. If the user has authorised application, then there will be a get request with code & scopes parameters.
        - With the code query parameter, we get the access and refresh token using oauth libraries after which we call to gmail api with query that we need only those emails whose subject contains "Bank Statement" to get user's email id and emails.
        - After we get the emails, we decode those emails using base64 library. We check for pdfs in the mail and if there are, then they are processed with controller function created.
        - The text is parsed on the assumption that the pdf of bank statements will contain this pattern "Date in mm/dd/yyyy" followed by description field, credit, debit and balance floats based on the templates of banks.
        - mm/dd/yyyy will not be considered as date without any numbers i.e. 11/12/2021 will be considered but mm/dd/yyyy will not be which is what is parsed from templates.It can be changed to consider mm/dd/yyyy as date as well though.
        - After then images are parsed and stored in attachments.
        - Then server responds to the request with json object containing a message of permissions being granted and the transactions which were extracted from the pdf file.

    - "/api/all_transactions"
        - Get request on this api point will be done with query parameter email which contains the gmail of which we are trying to get the data.
        - If the user has earlier provided permission for this email then it will be stored in the database along with its refresh and access tokens.
        - With the help of stored tokens, we make call to gmail API to get the emails of user after which processing of email in the same way as "/" api endpoint is done.

    - "/api/transactions"
        - Get request on this api point will be done with query parameter email and two other query parameters start_date and end_date which contains the gmail of which we are trying to get the data along with date range to get transactions within those range.
        - If the user has earlier provided permission for this email then it will be stored in the database along with its refresh and access tokens.
        - With the help of stored tokens, we make call to gmail API to get the emails of user after which processing of email in the same way as "/" api endpoint is done but in this case filter checks are applied in the code to get transactions from specific time range only.
    
    -"/api/total_balance"
       - Get request on this api point will be done with query parameter email which contains the gmail of which we are trying to get the data along with date query parameter (date of transactions).
       - If the user has earlier provided permission for this email then it will be stored in the database along with its refresh and access tokens.
        - With the help of stored tokens, we make call to gmail API to get the emails of user after which processing of email in the same way as other endpoints is done.
        - After all the transactions are collected , their dates are checked and compared with the given date and based on the decisions of the algorithm the total balance to be returned is affected and ultimately returned as response.

## Get All Transactions (GET)
``` baseUrl/api/all_transactions?email=adummy@gmail.com```

Command:
```
curl --location 'baseUrl/api/all_transactions' 
```

## Get Transactions On Date Range(GET)
``` baseUrl/api/transactions?email=adummy@gmail.com&start_date=11/22/2021&end_date=11/22/2021```

Command:
```
curl --location 'baseUrl/api/transactions' 
```
- Dates are in this format only : mm/dd/yyyy

## Get Total Balance On Date (GET)
``` baseUrl/api/total_balance?email=adummy@gmail.com&date=11/22/2021```

Command:
```
curl --location 'baseUrl/api/total_balance' 
```
## Get Permissions(GET)
``` baseUrl/api/?code=ajklds&scopes=kljkal```

- This endpoint will be hit only after user authorises application.
- For doing so user has to hit on "/" or "/index.html".
Command:
```
curl --location 'baseUrl/api/?code=ajklds&scopes=kljkal' 
```
## Setting up for Gmail API
- For using Gmail API, first make a project on google cloud console.
- In the Google Cloud console, go to Menu menu > APIs & Services > OAuth consent screen.

- Select the user type for your app, then click Create.
- Complete the app registration form, then click Save and Continue.
- Add test users.Only test users will be able to provide access to their gmails.
- Enter your email address and any other authorized test users, then click Save and Continue.
- Create user in the credentials of the application.
- In Authorized redirect URIs, add <b>http://localhost:8000/api/</b>
- Save the information and download json file containing credentials.
- Add that json file to the project directory with name credentials.json.

## Run Development server
Command:
```
    uvicorn main:app --reload
```
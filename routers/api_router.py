from fastapi import APIRouter, Request, Response, status, HTTPException, Query
from pydantic import BaseModel
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import Flow
import json
import datetime
import base64
from starlette.responses import FileResponse
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
from pdf_processing_controller.process_pdf import process_pdf_file
from models.users import create_user, get_user_by_email, User, SessionLocal, update_user_attributes

api_router = APIRouter()
creds = {}
#replace client id with your actual client id. We can use .env files to get access to such data later
client_id = "846564856796-buijq3n3gipunu1acpfjcdqsql68mo25.apps.googleusercontent.com"
client_secret = "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"

with open('credentials.json', 'r') as f:
    creds = json.load(f)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

@api_router.get("/")
async def get_permission_and_transactions(req : Request, res : Response) : 
    code = req.query_params.get("code")
    error = req.query_params.get("error")
    if error :
        return FileResponse("errors-templates/access_denied.html")
    flow = Flow.from_client_config(
    creds, # client configuration
    scopes=SCOPES,
    redirect_uri="http://localhost:8000/api/"
)
    # Exchange the authorization code for a credentials object
    try :
        flow.fetch_token(code=code)

    # Handle the InvalidGrantError from oauthlib
    except InvalidGrantError as error:
        return FileResponse("errors-templates/link_expired.html")
        #raise HTTPException(status_code=400, detail="Invalid grant: Bad Request")
    
    # Get the credentials object
    cred = flow.credentials
    access_token = cred.token
    refresh_token = cred.refresh_token
    try:
        # Initialize the Gmail API
        service = build('gmail', 'v1', credentials=cred)
        
        # Use the Gmail API to get the user's profile, which includes their email address
        user_info = service.users().getProfile(userId='me').execute()
        user_email = user_info['emailAddress']
        print(user_email)

        #create a user in the database
        user = User(email=user_email, access_token=access_token, refresh_token=refresh_token)

        # Use the CRUD function to create the user in the database
        db = SessionLocal()
        already_present_user = get_user_by_email(db, user_email)
        if already_present_user :
            update_user_attributes(db,user_email,access_token=access_token,refresh_token=refresh_token)
        else :
            create_user(db, user)
        db.close()
        # Define the query to filter emails by subject
        query = 'subject:"Bank Statement"'

        # Fetch emails that match the query
        results = service.users().messages().list(userId='me', q=query, maxResults=10000).execute()
        messages = results.get('messages', [])

        #initialise the transactions_processed to hold transactions
        transactions_processed = []
        if not messages:
            print('No messages found.')
        else:
            print('Messages:')
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id']).execute()

                # Get the message's subject and body
                subject = None
                body = None
                headers = msg['payload']['headers']
                for d in headers:
                    if d['name'] == 'Subject':
                        subject = d['value']
                if 'parts' in msg['payload']:
                    for part in msg['payload']['parts']:
                        
                        if part.get('mimeType', '').lower() == 'application/pdf':
                            # This is a PDF attachment
                            if 'data' in part['body']:
                                data = part['body']['data']
                            else:
                                att_id = part['body'].get('attachmentId')
                                if att_id:
                                    att = service.users().messages().attachments().get(userId='me', messageId=message['id'], id=att_id).execute()
                                    data = att.get('data', '')
                                else:
                                    print("No 'attachmentId' key in the 'body' dictionary for this part.")
                                    continue

                            # Process the PDF using pdfplumber & PyMupdf
                            file_data = base64.urlsafe_b64decode(data)
                            transactions_from_pdf = process_pdf_file(file_data)
                            
                            #add the transactions processed from the pdf using the process_pdf_file to final transactions
                            for t in transactions_from_pdf : 
                                transactions_processed.append([t.date, t.description, t.credit, t.debit, t.balance])
                        
                        elif part.get('mimeType', '').lower() == 'text/plain':
                            # This is plain text content in the email body
                            if 'data' in part['body']:
                                text_data = part['body']['data']
                                decoded_text = base64.urlsafe_b64decode(text_data).decode('utf-8')
                                body = decoded_text
                            else:
                                print("No 'data' key in the 'body' dictionary for text/plain content.")
                if subject:
                    print("Subject:", subject)
                if body:
                    print("Email Body:", body)
        return {
            "message" : "Permissions provided successfully",
            "transactions_processed" : transactions_processed
            }
    
    # Handle errors from gmail API.
    except HttpError as error:
        raise HTTPException(status_code="500", details=f"{error}")
    
    # Handle other general exceptions
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"{error}")
    

# handle transactions bw 2 dates
class DateRange(BaseModel):
    start_date: str
    end_date: str
def is_valid_date(date_str):
    try:
        # Attempt to parse the date string as a date with the format mm/dd/yyyy
        datetime.datetime.strptime(date_str, '%m/%d/%Y')
        return True
    except ValueError:
        return False

#endpoint to handle get all transactions 
@api_router.get("/all_transactions")
async def get_all_transactions(email : str) :
    
    # Get the user from the database based on the provided email
    db = SessionLocal()
    user = get_user_by_email(db, email)
    db.close()

    if user:
        # User exists, retrieve access_token and refresh_token
        access_token = user.access_token
        refresh_token = user.refresh_token
        creds = Credentials.from_authorized_user_info({
            'token': access_token,
            'refresh_token': refresh_token,
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': client_id,
            'client_secret': client_secret
        })
        try :
            # Build the Gmail API service
            service = build('gmail', 'v1', credentials=creds)
            query = 'subject:"Bank Statement"'

            # Fetch emails that match the query
            results = service.users().messages().list(userId='me', q=query, maxResults=10000).execute()
            messages = results.get('messages', [])
            transactions_processed = []
            if not messages:
                print('No messages found.')
            else:
                print('Messages:')
                for message in messages:
                    msg = service.users().messages().get(userId='me', id=message['id']).execute()

                    # Get the message's subject and body
                    subject = None
                    body = None
                    headers = msg['payload']['headers']
                    for d in headers:
                        if d['name'] == 'Subject':
                            subject = d['value']
                    if 'parts' in msg['payload']:
                        for part in msg['payload']['parts']:
                            
                            if part.get('mimeType', '').lower() == 'application/pdf':
                                # This is a PDF attachment
                                if 'data' in part['body']:
                                    data = part['body']['data']
                                else:
                                    att_id = part['body'].get('attachmentId')
                                    if att_id:
                                        att = service.users().messages().attachments().get(userId='me', messageId=message['id'], id=att_id).execute()
                                        data = att.get('data', '')
                                    else:
                                        print("No 'attachmentId' key in the 'body' dictionary for this part.")
                                        continue

                                # Process the PDF using pdfplumber & PyMupdf
                                file_data = base64.urlsafe_b64decode(data)
                                transactions_from_pdf = process_pdf_file(file_data)
                                
                                #add the transactions processed from the pdf using the process_pdf_file to final transactions
                                for t in transactions_from_pdf : 
                                    transactions_processed.append([t.date, t.description, t.credit, t.debit, t.balance])
                            
                            elif part.get('mimeType', '').lower() == 'text/plain':
                                # This is plain text content in the email body
                                if 'data' in part['body']:
                                    text_data = part['body']['data']
                                    decoded_text = base64.urlsafe_b64decode(text_data).decode('utf-8')
                                    body = decoded_text
                                else:
                                    print("No 'data' key in the 'body' dictionary for text/plain content.")
                    if subject:
                        print("Subject:", subject)
                    if body:
                        print("Email Body:", body)
                return {"transactions_processed" : transactions_processed}
        except HttpError as error:
            raise HTTPException(status_code="500", details=f"{error}")
    else:
        # User does not exist, return an error indicating permissions aren't provided
        raise HTTPException(status_code=403, detail="Permissions are not provided to access Gmail for the provided email.")

#Endpoint to handle transactions on specific date ranges
@api_router.get("/transactions")
async def get_transactions_bw_dates(email: str, start_date: str = Query(..., regex=r'\d{2}/\d{2}/\d{4}'),
                                    end_date: str = Query(..., regex=r'\d{2}/\d{2}/\d{4}')):
    
    # Check if the start_date and end_date have the correct format
    if not (is_valid_date(start_date) and is_valid_date(end_date)):
        raise HTTPException(status_code=400, detail="Invalid date format. Dates should be in mm/dd/yyyy format.")

    # Check if start_date is less than end_date
    start_datetime = datetime.datetime.strptime(start_date, '%m/%d/%Y')
    end_datetime = datetime.datetime.strptime(end_date, '%m/%d/%Y')
    if start_datetime >= end_datetime:
        raise HTTPException(status_code=400, detail="Start date must be before end date.")
    
    # Get the user from the database based on the provided email
    db = SessionLocal()
    user = get_user_by_email(db, email)
    db.close()

    if user:
        # User exists, retrieve access_token and refresh_token
        access_token = user.access_token
        refresh_token = user.refresh_token

        #print(f"Email: {email}, Start Date: {start_date}, End Date: {end_date}")
        #print(f"Access Token: {access_token}, Refresh Token: {refresh_token}")
        creds = Credentials.from_authorized_user_info({
            'token': access_token,
            'refresh_token': refresh_token,
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': client_id,
            'client_secret': client_secret
        })
        try :
            # Build the Gmail API service
            service = build('gmail', 'v1', credentials=creds)
            query = 'subject:"Bank Statement"'

            # Fetch emails that match the query
            results = service.users().messages().list(userId='me', q=query, maxResults=10000).execute()
            messages = results.get('messages', [])
            transactions_processed = []
            if not messages:
                print('No messages found.')
            else:
                print('Messages:')
                for message in messages:
                    msg = service.users().messages().get(userId='me', id=message['id']).execute()

                    # Get the message's subject and body
                    subject = None
                    body = None
                    headers = msg['payload']['headers']
                    for d in headers:
                        if d['name'] == 'Subject':
                            subject = d['value']
                    if 'parts' in msg['payload']:
                        for part in msg['payload']['parts']:
                            
                            if part.get('mimeType', '').lower() == 'application/pdf':
                                # This is a PDF attachment
                                if 'data' in part['body']:
                                    data = part['body']['data']
                                else:
                                    att_id = part['body'].get('attachmentId')
                                    if att_id:
                                        att = service.users().messages().attachments().get(userId='me', messageId=message['id'], id=att_id).execute()
                                        data = att.get('data', '')
                                    else:
                                        print("No 'attachmentId' key in the 'body' dictionary for this part.")
                                        continue

                                # Process the PDF using pdfplumber & PyMupdf
                                file_data = base64.urlsafe_b64decode(data)
                                transactions_from_pdf = process_pdf_file(file_data,start_date=start_date,end_date=end_date)
                                
                                #add the transactions processed from the pdf using the process_pdf_file to final transactions
                                for t in transactions_from_pdf : 
                                    transactions_processed.append([t.date, t.description, t.credit, t.debit, t.balance])
                            
                            elif part.get('mimeType', '').lower() == 'text/plain':
                                # This is plain text content in the email body
                                if 'data' in part['body']:
                                    text_data = part['body']['data']
                                    decoded_text = base64.urlsafe_b64decode(text_data).decode('utf-8')
                                    body = decoded_text
                                else:
                                    print("No 'data' key in the 'body' dictionary for text/plain content.")
                    if subject:
                        print("Subject:", subject)
                    if body:
                        print("Email Body:", body)
                return {"transactions_processed" : transactions_processed}
        except HttpError as error:
            raise HTTPException(status_code="500", details=f"{error}")
    else:
        # User does not exist, return an error indicating permissions aren't provided
        raise HTTPException(status_code=403, detail="Permissions are not provided to access Gmail for the provided email.")

# End-point to handle the request to get total_balance on specific date
@api_router.get("/total_balance")
async def get_balance_on_specific_date(email : str, date : str = Query(..., regex=r'\d{2}/\d{2}/\d{4}')) :
    # Check if the date has the correct format mm/dd/yyyy
    if not (is_valid_date(date)):
        raise HTTPException(status_code=400, detail="Invalid date format. Dates should be in mm/dd/yyyy format.")
    # Get today's date
    today_date = datetime.datetime.now()
    
    if datetime.datetime.strptime(date, '%m/%d/%Y') > today_date:
        raise HTTPException(status_code=400, detail="Date should be less than today's date.")

        # Get the user from the database based on the provided email
    db = SessionLocal()
    user = get_user_by_email(db, email)
    db.close()

    if user:
        # User exists, retrieve access_token and refresh_token
        access_token = user.access_token
        refresh_token = user.refresh_token
        creds = Credentials.from_authorized_user_info({
            'token': access_token,
            'refresh_token': refresh_token,
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': client_id,
            'client_secret': client_secret
        })
        try :
            # Build the Gmail API service
            service = build('gmail', 'v1', credentials=creds)
            query = 'subject:"Bank Statement"'

            # Fetch emails that match the query
            results = service.users().messages().list(userId='me', q=query, maxResults=10000).execute()
            messages = results.get('messages', [])
            total_balance = 0
            if not messages:
                print('No messages found.')
            else:
                print('Messages:')
                for message in messages:
                    msg = service.users().messages().get(userId='me', id=message['id']).execute()

                    # Get the message's subject and body
                    subject = None
                    body = None
                    headers = msg['payload']['headers']
                    for d in headers:
                        if d['name'] == 'Subject':
                            subject = d['value']
                    if 'parts' in msg['payload']:
                        for part in msg['payload']['parts']:
                            
                            if part.get('mimeType', '').lower() == 'application/pdf':
                                # This is a PDF attachment
                                if 'data' in part['body']:
                                    data = part['body']['data']
                                else:
                                    att_id = part['body'].get('attachmentId')
                                    if att_id:
                                        att = service.users().messages().attachments().get(userId='me', messageId=message['id'], id=att_id).execute()
                                        data = att.get('data', '')
                                    else:
                                        print("No 'attachmentId' key in the 'body' dictionary for this part.")
                                        continue

                                # Process the PDF using pdfplumber & PyMupdf
                                file_data = base64.urlsafe_b64decode(data)
                                transactions = process_pdf_file(file_data)
                                transactions = sorted(transactions, key=lambda t:t.date)
                                balance_to_added_from_this_pdf = -10
                                is_transactions_with_less_date_present = False
                                is_transactions_with_larger_date_present = False
                                nearest_balance = 0
                                #add the transactions processed from the pdf using the process_pdf_file to final transactions
                                for t in transactions: 
                                    if t.date == date:
                                        balance_to_added_from_this_pdf = t.balance
                                    elif t.date < date:
                                        is_transactions_with_less_date_present =True
                                        nearest_balance = t.balance
                                    elif t.date > date:
                                        is_transactions_with_larger_date_present = True
                                if balance_to_added_from_this_pdf == -10 :
                                    if is_transactions_with_larger_date_present and is_transactions_with_less_date_present :
                                        balance_to_added_from_this_pdf = nearest_balance
                                    else :
                                        balance_to_added_from_this_pdf = 0
                                total_balance += balance_to_added_from_this_pdf
                            elif part.get('mimeType', '').lower() == 'text/plain':
                                # This is plain text content in the email body
                                if 'data' in part['body']:
                                    text_data = part['body']['data']
                                    decoded_text = base64.urlsafe_b64decode(text_data).decode('utf-8')
                                    body = decoded_text
                                else:
                                    print("No 'data' key in the 'body' dictionary for text/plain content.")
                    if subject:
                        print("Subject:", subject)
                    if body:
                        print("Email Body:", body)
            return {"total_balance" : total_balance}
        except HttpError as error :
            raise HTTPException(status_code="500", details=f"{error}")
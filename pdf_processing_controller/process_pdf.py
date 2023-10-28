import pdfplumber
import os
import io
import fitz  # PyMuPDF
import datetime
import re

class Transaction:
    def __init__(self, date, description, credit, debit, balance):
        self.date = date
        self.description = description
        self.credit = credit
        self.debit = debit
        self.balance = balance

def process_pdf_file(file_data,start_date=None, end_date=None):
    #text is extracted using PyMuPDF library
    pdf_file = fitz.open(stream=io.BytesIO(file_data), filetype="pdf")
    text = ""

    for page_num in range(len(pdf_file)):
        page = pdf_file[page_num]
        text += page.get_text()
    
    #print("pdf is being processed")
    #print(text)
    
    #text will be of below like form. uncomment this to check transactions result look like  
    #text = "11/11/2021\ndksl\njkaz\n11/11/2021\ndksl\n789.90\n7890\n1900\n11/21/2021\ndksl\n789.90\n7890\n1900\n12/12/2022\ndksl\n789.90\n7890\n1900"
    if start_date :
        transactions = pick_transactions_from_text(text=text,start_date=start_date,end_date=end_date)
    else :
        transactions = pick_transactions_from_text(text=text)
    #images will be exracted using pdfplumber library
    pdf = pdfplumber.open(io.BytesIO(file_data))
    image_dir = "attachments/"
    page = pdf.pages[0]
    os.makedirs(image_dir, exist_ok=True)
    images = page.images
    for i, image in enumerate(images):
        x0, y0, x1, y1 = image["x0"], image["y0"], image["x1"], image["y1"]
        
        # Extract the image using the coordinates
        img = page.crop((x0, y0, x1, y1))
        img = img.to_image()
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

        # Define the image filename with a timestamp
        image_filename = os.path.join(image_dir, f"image_{i}_{timestamp}.png")

        # Save the image to the specified directory
        img.save(image_filename, "PNG")

    pdf.close()

    return transactions

#function which will filter transactions out of text if start_date & end_date are provided then will provide transactions b/w those else will provide all transactions
def pick_transactions_from_text(text,start_date=None, end_date=None) : 
    lines = text.split('\n')
    #print(lines)
    print("in transactions")
    print(start_date,end_date)
    transactions = []

    # Define a regular expression to match date patterns (mm/dd/yyyy)
    date_pattern = re.compile(r"\d{1,2}/\d{1,2}/\d{4}")

    # Initialize variables to store transaction data
    current_transaction = []

    for line in lines:
        stripped_line = line.strip()
        
        # Check if the line matches the date pattern
        if date_pattern.match(stripped_line):
            current_transaction = [stripped_line]  # Start a new transaction
            continue
        
        if current_transaction:
            # If a transaction has started, continue collecting data
            current_transaction.append(stripped_line)
            
            # Check if we have collected 5 lines (1 date, 1 description, 3 floats for credit, debit, balance)
            if len(current_transaction) == 5:
                date, description, credit, debit, balance = current_transaction
                date = date.strip()
                description = description.strip()
                credit = float(credit.replace(",", ""))
                debit = float(debit.replace(",", ""))
                balance = float(balance.replace(",",""))
                 # Check if the date is within the specified range (if start_date and end_date are provided)
                if start_date and end_date:
                    transaction_date = datetime.datetime.strptime(date, '%m/%d/%Y')
                    print(type(start_date))
                    s_date = datetime.datetime.strptime(start_date, '%m/%d/%Y')
                    e_date = datetime.datetime.strptime(end_date,'%m/%d/%Y')
                    if s_date <= transaction_date <= e_date:
                        transactions.append(Transaction(date, description, credit, debit, balance))
                else:
                    transactions.append(Transaction(date, description, credit, debit, balance))

                current_transaction = []  # Reset variables for the next transaction

    # Print the extracted transactions
    # for transaction in transactions:
    #     print(f"Date: {transaction.date}")
    #     print(f"Description: {transaction.description}")
    #     print(f"Credit: {transaction.credit}")
    #     print(f"Debit: {transaction.debit}")
    #     print(f"Balance: {transaction.balance}")
    #     print()

    return transactions
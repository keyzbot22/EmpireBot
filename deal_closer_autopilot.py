#!/usr/bin/env python3
"""
EmpireBot Autopilot Deal Closer
v3.1 – Fully Automated Outreach + Contract Generation
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from twilio.rest import Client as TwilioClient
from email.message import EmailMessage
import smtplib
from google.oauth2 import service_account
from googleapiclient.discovery import build as google_build

# Load .env variables
load_dotenv()

class DealCloserBot:
    def __init__(self):
        # Initialize Twilio
        self.twilio = TwilioClient(
            os.getenv('TWILIO_SID'),
            os.getenv('TWILIO_TOKEN')
        )
        self.twilio_from = os.getenv('TWILIO_PHONE')

        # Initialize Zoho Email
        self.email_config = {
            'server': 'smtp.zoho.com',
            'port': 587,
            'user': os.getenv('ZOHO_EMAIL'),
            'password': os.getenv('ZOHO_APP_PASSWORD')
        }

        # Load Google credentials
        creds = service_account.Credentials.from_service_account_file(
            'service-account.json',
            scopes=[
                'https://www.googleapis.com/auth/documents',
                'https://www.googleapis.com/auth/drive'
            ]
        )
        self.contract_service = google_build('docs', 'v1', credentials=creds)
        self.drive_service = google_build('drive', 'v3', credentials=creds)

        # Templates
        self.sms_template = "Hi {name}, this is Keys from Aura Market. Interested in your property at {address}. Can we talk?"
        self.email_template = """Subject: Cash Offer for {address}

Hi {name},

We're ready to make a cash offer on your property:
{address}

Offer Price: ${price}
Close: 10–14 days
No repairs required.

Contract link is included. Contact us at (877) 780-4236.

Best,  
Keys  
Aura Market Team  
"""

    def generate_contract(self, seller_info):
        template_id = '1QJjW9x4YH6v8bL0zP2cR7mN3kS5dF9e'  # Replace with your actual template ID

        # Copy the file in Drive
        file_metadata = {
            'name': f"Contract_{seller_info['name']}_{datetime.now().date()}",
        }
        copied_file = self.drive_service.files().copy(
            fileId=template_id,
            body=file_metadata
        ).execute()

        document_id = copied_file['id']

        # Fill placeholders
        requests = [
            {'replaceAllText': {'containsText': {'text': '{{NAME}}', 'matchCase': True}, 'replaceText': seller_info['name']}},
            {'replaceAllText': {'containsText': {'text': '{{ADDRESS}}', 'matchCase': True}, 'replaceText': seller_info['address']}},
            {'replaceAllText': {'containsText': {'text': '{{PRICE}}', 'matchCase': True}, 'replaceText': seller_info['price']}}
        ]
        self.contract_service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute()

        return f"https://docs.google.com/document/d/{document_id}"

    def send_sms(self, lead):
        self.twilio.messages.create(
            body=self.sms_template.format(name=lead['name'], address=lead['address']),
            from_=self.twilio_from,
            to=lead['phone']
        )

    def send_email(self, lead, contract_url):
        msg = EmailMessage()
        msg.set_content(self.email_template.format(
            name=lead['name'],
            address=lead['address'],
            price=lead['price']
        ) + f"\nContract: {contract_url}")

        msg['Subject'] = f"Cash Offer for {lead['address']}"
        msg['From'] = self.email_config['user']
        msg['To'] = lead['email']

        with smtplib.SMTP(self.email_config['server'], self.email_config['port']) as server:
            server.starttls()
            server.login(self.email_config['user'], self.email_config['password'])
            server.send_message(msg)

    def run(self):
        # Sample lead (auto mode — no input needed)
        lead = {
            'name': 'John Smith',
            'address': '123 Main St, Miami, FL',
            'price': '350000',
            'phone': '+13057136709',
            'email': 'keyzbrands@gmail.com'
        }

        print(f"📞 Reaching out to {lead['name']}...")

        self.send_sms(lead)
        contract_url = self.generate_contract(lead)
        self.send_email(lead, contract_url)

        print(f"""
✅ Deal Outreach Sent:
• SMS: Success
• Email: Sent to {lead['email']}
• Contract: {contract_url}
        """)

if __name__ == '__main__':
    bot = DealCloserBot()
    bot.run()


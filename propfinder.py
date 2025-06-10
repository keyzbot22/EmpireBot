import os
import pandas as pd
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import requests

# Config
SCOPES = ['https://www.googleapis.com/auth/drive.file']
TOKEN_PATH = 'token.json'
CREDENTIALS_PATH = 'credentials.json'
FOLDER_ID = '1RUc2hzPx2GhnPumkqg4M1O2LuBjjj377'  # EmpireBot_Ebooks
BOT_TOKEN = '7329634509:AAG2sydFNeF02HuNYV8L9fDDXZViecXa7uA'
CHAT_ID = '1477503070'

def generate_property_file(cities):
    properties = [
        {"Address": "123 Main St, Miami", "Price": 350000, "Beds": 3},
        {"Address": "456 Palm Ave, Tampa", "Price": 275000, "Beds": 2},
    ]
    df = pd.DataFrame(properties)
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"EmpireDeals_{today}_{'_'.join(cities)}.xlsx"
    df.to_excel(filename, index=False)
    return filename

def upload_to_drive(filename):
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {
        'name': filename,
        'parents': [FOLDER_ID],
        'mimeType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }
    media = MediaFileUpload(filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return f"https://drive.google.com/file/d/{file['id']}/view?usp=sharing"

def send_telegram_alert(filename, link):
    message = f"🚨 *New Property Deals Uploaded!*\n📄 `{filename}`\n🔗 [View on Google Drive]({link})"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"})

if __name__ == "__main__":
    cities = ["Miami", "Tampa", "Orlando"]
    filename = generate_property_file(cities)
    link = upload_to_drive(filename)
    send_telegram_alert(filename, link)
    print(f"✅ Uploaded {filename} and sent Telegram alert!")


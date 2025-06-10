import csv
import requests

TELEGRAM_BOT_TOKEN = '7329634509:AAG2sydFNeF02HuNYVV9fDDXZViecXa7uA'
TELEGRAM_CHAT_ID = '1477503070'

def load_buyers():
    with open('buyers.csv', newline='') as f:
        return list(csv.DictReader(f))

def load_leads():
    with open('leads.csv', newline='') as f:
        return list(csv.DictReader(f))

def notify_telegram(message):
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data=payload)

def match_buyers_to_leads():
    buyers = load_buyers()
    leads = load_leads()

    for lead in leads:
        for buyer in buyers:
            if lead['city'] in buyer['locations']:
                message = (
                    f"📢 *Buyer Match Found!*\n\n"
                    f"*Buyer:* {buyer['name']}\n"
                    f"*Phone:* {buyer['phone']}\n"
                    f"*Email:* {buyer['email']}\n"
                    f"*Interested In:* {buyer['locations']}\n\n"
                    f"*Property:* {lead['address']} in {lead['city']}, {lead['state']}\n"
                    f"*Asking:* ${lead['price']}\n"
                    f"*Contact Seller:* {lead['phone']} | {lead['email']}"
                )
                notify_telegram(message)

if __name__ == '__main__':
    match_buyers_to_leads()


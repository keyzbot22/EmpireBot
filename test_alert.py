import requests

bot_token = "7538838886:AAHxPw8w1epf5i5PMcd4X_xoaRR6_MfOApE"
admin_chat_id = "1477503070"
message = "🚨 TEST ALERT: ZariahBot and EmpireBot fully online. Confirm receipt."

url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
payload = {
    "chat_id": admin_chat_id,
    "text": message,
    "parse_mode": "Markdown"
}

response = requests.post(url, data=payload)
print(response.json())


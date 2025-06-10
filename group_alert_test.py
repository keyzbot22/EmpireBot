import requests

bot_token = "7538838886:AAHxPw8w1epf5i5PMcd4X_xoaRR6_MfOApE"
group_chat_id = -4907469487  # Your Telegram group ID

payload = {
    "chat_id": group_chat_id,
    "text": "🚨 *GROUP ALERT TEST:* ZariahBot & EmpireBot are live and watching.\nReply with /status to confirm system activity.",
    "parse_mode": "Markdown"
}

url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
response = requests.post(url, data=payload)
print(response.json())


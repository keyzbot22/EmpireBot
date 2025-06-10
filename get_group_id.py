import requests

bot_token = "7538838886:AAHxPw8w1epf5i5PMcd4X_xoaRR6_MfOApE"
url = f"https://api.telegram.org/bot{bot_token}/getUpdates"

response = requests.get(url)
print(response.json())


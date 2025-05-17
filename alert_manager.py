import os
import requests

class AlertManager:
    def __init__(self):
        pass  # No SafeRequest needed

    def send(self, message):
        token = os.getenv("EMPIRE_BOT_TOKEN")
        chat_id = os.getenv("ADMIN_CHAT_ID", "123456")
        return requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
        )

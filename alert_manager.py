import os
from utils.http import SafeRequest

class AlertManager:
    def __init__(self):
        self.http = SafeRequest()

    def send(self, message):
        token = os.getenv("EMPIRE_BOT_TOKEN")
        chat_id = os.getenv("ADMIN_CHAT_ID", "123456")
        return self.http.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
        )

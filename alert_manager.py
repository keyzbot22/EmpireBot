# === SafeRequest (utils/http.py) ===
import requests
import time
from datetime import datetime

class SafeRequest:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'EmpireBot/2.0'})

    def post(self, url, payload, max_retries=3, timeout=5):
        last_error = None
        for attempt in range(max_retries):
            try:
                response = self.session.post(url, json=payload, timeout=timeout)
                if response.status_code < 500:
                    return response.json()
            except Exception as e:
                last_error = str(e)
                time.sleep(2 ** attempt)
        return {
            "error": "request_failed",
            "message": last_error,
            "attempts": max_retries
        }

# === AlertManager (alerts/manager.py) ===
import os
from utils.http import SafeRequest

class AlertManager:
    def __init__(self):
        self.http = SafeRequest()
        self.telegram_endpoint = "https://api.telegram.org/bot{token}/sendMessage"

    def send(self, message):
        result = self._send_telegram(os.getenv('EMPIRE_BOT_TOKEN'), message)
        if not result.get('ok'):
            for bot_token in [
                os.getenv('ZARIAH_BOT_TOKEN'),
                os.getenv('KEYCONTROL_BOT_TOKEN')
            ]:
                result = self._send_telegram(bot_token, message)
                if result.get('ok'):
                    break
        return result

    def _send_telegram(self, token, message):
        return self.http.post(
            self.telegram_endpoint.format(token=token),
            {
                "chat_id": os.getenv('ADMIN_CHAT_ID'),
                "text": message,
                "parse_mode": "HTML"
            }
        )

# === Flask App (main file) ===
from flask import Flask, jsonify
import os
from alerts.manager import AlertManager

app = Flask(__name__)
alert_manager = AlertManager()

@app.route("/test-alerts", methods=["POST"])
def test_alerts():
    result = alert_manager.send("🔥 Test Alert from EmpireBot")
    return jsonify(result)

@app.route("/alert-status")
def alert_status():
    return jsonify({
        "telegram": {
            "empire": check_bot_online(os.getenv('EMPIRE_BOT_TOKEN')),
            "zariah": check_bot_online(os.getenv('ZARIAH_BOT_TOKEN')),
            "keycontrol": check_bot_online(os.getenv('KEYCONTROL_BOT_TOKEN'))
        }
    })

def check_bot_online(token):
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=3)
        return resp.json().get('ok', False)
    except:
        return False

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))

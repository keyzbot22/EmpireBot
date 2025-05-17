# empirebot_prod.py
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from alerts.manager import AlertManager
from flask import Flask, jsonify
from datetime import datetime

app = Flask(__name__)
alert_manager = AlertManager()

@app.route('/')
def index():
    return jsonify({"status": "running", "timestamp": datetime.utcnow().isoformat()})

@app.route('/test-alerts', methods=['GET'])
def test_alerts():
    message = f"\u26a0\ufe0f EmpireBot Test Alert - {datetime.utcnow().isoformat()}"
    result = alert_manager.send(message)
    return jsonify({"result": result})

# alerts/manager.py
import os
from utils.http import SafeRequest

class AlertManager:
    def __init__(self):
        self.http = SafeRequest()
        self.token = os.getenv('EMPIRE_BOT_TOKEN')
        self.chat_id = os.getenv('ADMIN_CHAT_ID')

    def send(self, message):
        return self.http.post(
            f"https://api.telegram.org/bot{self.token}/sendMessage",
            {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
        )

# utils/http.py
import requests

class SafeRequest:
    def post(self, url, payload):
        try:
            response = requests.post(url, json=payload, timeout=5)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

# setup.py
from setuptools import setup, find_packages

setup(
    name="empirebot",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'gunicorn',
        'gevent',
        'flask',
        'flask-jwt-extended',
        'flask-limiter',
        'prometheus-flask-exporter',
        'requests',
        'redis'
    ],
)

# requirements.txt
gunicorn
gevent
flask
flask-jwt-extended
flask-limiter
prometheus-flask-exporter
requests
redis

# alerts/__init__.py
# (empty file)

# utils/__init__.py
# (empty file)

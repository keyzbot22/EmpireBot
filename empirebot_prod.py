# empirebot_prod.py
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from prometheus_flask_exporter import PrometheusMetrics

# Ensure current directory is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from alerts.manager import AlertManager

# === Config ===
class Config:
    def __init__(self):
        self.SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(32).hex())
        self.JWT_SECRET = os.getenv("JWT_SECRET", os.urandom(32).hex())
        self.ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

config = Config()

# === Flask App ===
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = config.JWT_SECRET
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

jwt = JWTManager(app)

# === Limiter ===
try:
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        from redis import Redis
        Redis.from_url(redis_url).ping()
        limiter = Limiter(app=app, key_func=get_remote_address, storage_uri=redis_url)
    else:
        raise ValueError("Missing REDIS_URL")
except Exception:
    limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["200/hour"])

# === Metrics ===
metrics = PrometheusMetrics(app)
metrics.info('app_info', 'EmpireBot Monitoring', version='6.3.3')

# === Alert Manager ===
alert_manager = AlertManager()

# === Routes ===
@app.route('/')
def index():
    return jsonify({"status": "running", "version": "6.3.3"})

@app.route('/test-alerts', methods=['GET'])
def test_alerts():
    msg = f"\ud83d\udea8 EmpireBot System Test\nTimestamp: {datetime.now().isoformat()}"
    result = alert_manager.send(msg)
    return jsonify({"status": "ok" if result.get("ok") else "fail", "response": result})

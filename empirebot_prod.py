# empirebot_prod.py
import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from prometheus_flask_exporter import PrometheusMetrics

# Ensure root path is included
sys.path.insert(0, str(Path(__file__).parent))

try:
    from alerts.manager import AlertManager
except ImportError as e:
    print(f"ImportError: {e}")
    raise

# === Logging ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# === Config ===
class Config:
    def __init__(self):
        self.JWT_SECRET = os.getenv('JWT_SECRET', os.urandom(32).hex())
        self.ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID', '1477503070')

config = Config()

# === Flask Setup ===
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = config.JWT_SECRET
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
jwt = JWTManager(app)

# === Rate Limiting ===
try:
    redis_url = os.getenv('REDIS_URL')
    if redis_url and redis_url.startswith("redis://"):
        from redis import Redis
        Redis.from_url(redis_url).ping()
        limiter = Limiter(app=app, key_func=get_remote_address, storage_uri=redis_url)
        logger.info("✅ Redis rate limiting enabled")
    else:
        raise ValueError("Invalid or missing REDIS_URL")
except Exception as e:
    logger.warning(f"⚠️ Using in-memory rate limiter: {e}")
    limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["200/hour"])

# === Metrics ===
metrics = PrometheusMetrics(app)
metrics.info('app_info', 'EmpireBot Monitoring', version='6.3.3')

# === Alert Manager ===
alert_manager = AlertManager()

# === Routes ===
@app.route('/')
def index():
    return jsonify({
        "status": "running",
        "version": "6.3.3",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })

@app.route('/test-alerts', methods=['GET'])
def test_alerts():
    msg = f"🚨 EmpireBot System Test\nTimestamp: {datetime.now().isoformat()}"
    result = alert_manager.send(msg)
    return jsonify({
        "status": "success" if result.get('ok') else "failed",
        "bot_response": result,
        "timestamp": datetime.now().isoformat()
    }), 200

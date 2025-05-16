# empirebot_prod.py

import os
import json
import base64
import hmac
import hashlib
import logging
import sqlite3
import threading
import time
import requests
from queue import Queue
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, abort, render_template, send_file
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from prometheus_flask_exporter import PrometheusMetrics

from alerts.manager import AlertManager

# === Logging ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# === Config ===
class Config:
    def __init__(self):
        self.SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(32).hex())
        self.JWT_SECRET = os.getenv('JWT_SECRET', os.urandom(32).hex())
        self.ADMIN_USER = os.getenv('ADMIN_USER')
        self.ADMIN_PW = os.getenv('ADMIN_PW', 'ChangeMe!')
        self.ADMIN_PW_HASH = self.ADMIN_PW.encode('utf-8')
        self.SHOPIFY_API_SECRET = os.getenv('SHOPIFY_API_SECRET')
        self.ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID', '1477503070')

config = Config()

# === Flask ===
app = Flask(__name__, template_folder="templates")
app.config['JWT_SECRET_KEY'] = config.JWT_SECRET
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
app.config['JWT_COOKIE_SECURE'] = True
app.config['JWT_COOKIE_CSRF_PROTECT'] = True
jwt = JWTManager(app)

# === Rate Limiter ===
try:
    redis_url = os.getenv('REDIS_URL')
    if redis_url and redis_url.startswith("redis://"):
        from redis import Redis
        redis_client = Redis.from_url(redis_url)
        redis_client.ping()
        limiter = Limiter(app=app, key_func=get_remote_address, storage_uri=redis_url, strategy="moving-window", default_limits=["500/hour", "50/minute"])
        logger.info("✅ Redis rate limiting enabled")
    else:
        raise ValueError("REDIS_URL missing or invalid")
except Exception as e:
    logger.warning(f"⚠️ Using in-memory rate limiting: {str(e)}")
    limiter = Limiter(app=app, key_func=get_remote_address, storage_uri="memory://", strategy="moving-window", default_limits=["200/hour", "20/minute"])

# === Metrics ===
metrics = PrometheusMetrics(app)
metrics.info('app_info', 'EmpireBot Metrics', version='6.3.3')

# === Initialize AlertManager ===
alert_manager = AlertManager()

# === Routes ===
@app.route('/')
def health_check():
    return jsonify({
        "status": "running",
        "version": "6.3.3",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })

@app.route('/test-alerts', methods=['GET'])
def test_alerts():
    """Non-recursive test endpoint"""
    test_msg = (
        "🚨 EmpireBot System Test\n"
        f"Timestamp: {datetime.now().isoformat()}\n"
        "This confirms your alert system is operational"
    )

    result = alert_manager.send(test_msg)

    return jsonify({
        "status": "success" if result.get('ok') else "failed",
        "bot_response": result,
        "timestamp": datetime.now().isoformat()
    }), 200

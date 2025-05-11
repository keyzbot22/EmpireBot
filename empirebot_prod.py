# EmpireBot v6.1 - Autonomous Money Empire

import os
import time
import json
import base64
import hmac
import hashlib
import logging
import threading
import subprocess
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Any, Optional, List
import sqlite3
import random
import openai
import requests
import psutil
import stripe
import aiohttp
import asyncio

from flask import Flask, request, jsonify, abort, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from prometheus_client import start_http_server, Counter, Gauge
from logging.handlers import RotatingFileHandler
from flasgger import Swagger
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask App
app = Flask(__name__)
# ========== CONFIGURATION ==========
class Config:
    def __init__(self):
        self.SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(32).hex())
        self.JWT_SECRET = os.getenv('JWT_SECRET', os.urandom(32).hex())
        self.ADMIN_USER = os.getenv('ADMIN_USER', 'admin')
        self.ADMIN_PW_HASH = generate_password_hash(os.getenv('ADMIN_PW', 'ChangeMe!'))
        self.HEARTBEAT_INTERVAL = 300
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        self.ADMIN_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
        self.SUPERVISED_MODE = os.getenv('SUPERVISED_MODE', 'false') == 'true'
        self.METABASE_URL = os.getenv('METABASE_URL')
        self.DATABASE = 'empirebot.db'

config = Config()
app.config['JWT_SECRET_KEY'] = config.JWT_SECRET
jwt = JWTManager(app)
class Database:
    def __init__(self):
        self.lock = threading.Lock()
        self.conn = None

    def get_connection(self):
        if not self.conn:
            self.conn = sqlite3.connect(config.DATABASE, check_same_thread=False)
        return self.conn

    def init_db(self):
        with self.get_connection() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS shopify_orders (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    order_id TEXT UNIQUE,
                    total_price REAL,
                    items TEXT
                );
                CREATE TABLE IF NOT EXISTS queries (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    ip_address TEXT,
                    query TEXT,
                    response TEXT,
                    tokens_used INTEGER
                );
            ''')

db = Database()
def send_telegram(chat_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text}
        )
    except Exception as e:
        app.logger.error(f"Telegram error: {str(e)}")

class Orchestrator:
    def __init__(self):
        self.queues = {
            'zariah': asyncio.Queue()
        }

    async def dispatch(self):
        while True:
            for bot, queue in self.queues.items():
                if not queue.empty():
                    msg = await queue.get()
                    send_telegram(msg['chat_id'], msg['text'])
            await asyncio.sleep(1)

orchestrator = Orchestrator()
@app.route('/admin/login', methods=['POST'])
def admin_login():
    """Login to admin panel"""
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if username == config.ADMIN_USER and check_password_hash(config.ADMIN_PW_HASH, password):
        token = create_access_token(identity=username)
        return jsonify(access_token=token)
    abort(401, description="Invalid credentials")

@app.route('/admin/payouts', methods=['POST'])
@jwt_required()
def manual_payout():
    """Trigger Stripe payout manually"""
    data = request.get_json()
    amount = data.get("amount", 0)
    try:
        stripe.Payout.create(amount=int(amount), currency='usd')
        return jsonify({"status": "processed"})
    except Exception as e:
        app.logger.error(f"Payout error: {str(e)}")
        abort(500, description="Stripe payout failed")
# VA API key hashes (can be stored in .env)
va_keys = {
    "va1": generate_password_hash(os.getenv("VA1_KEY", "va_pass_1")),
    "va2": generate_password_hash(os.getenv("VA2_KEY", "va_pass_2"))
}

def va_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-KEY")
        for name, hashed in va_keys.items():
            if check_password_hash(hashed, key):
                return f(*args, **kwargs)
        abort(403, description="Forbidden")
    return decorated

@app.route('/va/orders', methods=['GET'])
@va_required
def view_orders():
    """Allow VAs to fetch recent order summaries"""
    with db.get_connection() as conn:
        rows = conn.execute("SELECT id, order_id, total_price FROM shopify_orders ORDER BY id DESC LIMIT 50").fetchall()
        return jsonify([
            {"id": r[0], "order_id": r[1], "total_price": r[2]} for r in rows
        ])
@app.route('/shopify/order', methods=['POST'])
def handle_order():
    """Shopify order webhook"""
    data = request.get_json()
    if not data or 'id' not in data:
        abort(400, description="Invalid Shopify order")

    order_id = data['id']
    total = float(data.get('total_price', 0))
    currency = data.get('currency', 'USD')
    items = json.dumps(data.get('line_items', []))

    try:
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO shopify_orders (timestamp, order_id, total_price, items) VALUES (?, ?, ?, ?)",
                (datetime.utcnow().isoformat(), order_id, total, items)
            )
    except sqlite3.IntegrityError:
        return jsonify({"status": "duplicate"}), 200

    # Trigger Upsell or Whale alert
    if total > 1000:
        send_telegram(config.ADMIN_CHAT_ID, f"🚨 WHALE ORDER: ${total} - Order #{order_id}")
        orchestrator.queues['zariah'].put((0, {
            "chat_id": config.ADMIN_CHAT_ID,
            "text": "🧠 Upsell Triggered: Send VIP CODE WHALE15"
        }))

    # Stripe payout
    if data.get("gateway", "").lower() == "stripe":
        try:
            stripe.Payout.create(
                amount=int(total * 100),
                currency=currency.lower()
            )
        except Exception as e:
            app.logger.error(f"Stripe payout failed: {str(e)}")

    # Crypto alert
    if currency.upper() == "USDT":
        send_telegram(config.ADMIN_CHAT_ID, f"💎 Crypto Payment Received: ${total} USDT")

    return jsonify({"status": "processed"}), 200
def optimize_profits():
    """Run hourly and suggest pricing strategies via AI"""
    while True:
        try:
            with db.get_connection() as conn:
                avg, count = conn.execute(
                    "SELECT AVG(total_price), COUNT(*) FROM shopify_orders WHERE timestamp >= datetime('now', '-1 day')"
                ).fetchone()

            strategy = "📈 RAISE PRICES" if avg > 200 else "🛑 HOLD PRICING"

            ai_response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{
                    "role": "system",
                    "content": f"Given an avg order value of ${avg:.2f} from {count} orders, suggest 1 pricing tweak."
                }]
            )

            suggestion = ai_response.choices[0].message["content"]

            orchestrator.queues['empire'].put((1, {
                "chat_id": config.ADMIN_CHAT_ID,
                "text": f"{strategy}\n{suggestion}"
            }))

        except Exception as e:
            app.logger.error(f"Profit optimizer error: {str(e)}")
        time.sleep(3600)
def is_fraudulent(order):
    billing_country = order.get("billing_address", {}).get("country_code", "")
    shipping_country = order.get("shipping_address", {}).get("country_code", "")
    total = float(order.get("total_price", 0))

    # Basic geo mismatch or abnormal order value
    return billing_country and shipping_country and billing_country != shipping_country or total > 5000

@app.before_request
def verify_hmac():
    if request.path.startswith('/shopify'):
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256', '')
        digest = base64.b64encode(hmac.new(
            os.getenv('SHOPIFY_API_SECRET', '').encode(),
            request.data,
            hashlib.sha256
        ).digest()).decode()

        if not hmac.compare_digest(digest, hmac_header):
            abort(403, description="HMAC validation failed")
            # ================== v6.2 SECURITY PATCH ==================
import bcrypt
from flask_jwt_extended import get_jwt

# ========== STRONGER ADMIN AUTH ==========  
# Replace old admin password setup with:
config.ADMIN_PW_HASH = bcrypt.hashpw(
    os.getenv("ADMIN_PW", "ChangeMe!").encode("utf-8"),
    bcrypt.gensalt()
)

@app.route('/admin/login', methods=['POST'])
@limiter.limit("5 per minute")
def admin_login():
    username = request.json.get('username')
    password = request.json.get('password')

    if not username or not password:
        abort(400, description="Missing credentials")

    if username == config.ADMIN_USER and bcrypt.checkpw(password.encode('utf-8'), config.ADMIN_PW_HASH):
        additional_claims = {"is_admin": True}
        access_token = create_access_token(identity=username, additional_claims=additional_claims)
        return jsonify(access_token=access_token)
    else:
        abort(401, description="Invalid credentials")

# ========== ADMIN-ONLY DECORATOR ==========
def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if not claims.get("is_admin"):
            abort(403, description="Admins only")
        return fn(*args, **kwargs)
    return wrapper

# Apply this decorator to sensitive endpoints
@app.route('/admin/marketing', methods=['GET'])
@admin_required
def marketing_dashboard():
    top_influencers = marketing_engine.get_top_influencers()
    return jsonify({
        "top_influencers": top_influencers,
        "conversion_rates": {
            "organic": 0.03,
            "paid": 0.12,
            "influencer": 0.21
        }
    })

# ========== INPUT VALIDATION PATCHES ==========
class SecureMarketingEngine(MarketingEngine):
    def add_influencer(self, name: str, platform: str, rate: float = 0.15):
        if not name.strip() or not platform.strip():
            raise ValueError("Missing required fields")
        if not isinstance(rate, float) or not (0 <= rate <= 1):
            raise ValueError("Invalid commission rate")
        return super().add_influencer(name, platform, rate)

# ========== REPLACE ENGINE IF NEEDED ==========
marketing_engine = SecureMarketingEngine()

# ========== ENHANCED HEALTH CHECK ==========
@app.route('/health', methods=['GET'])
def secure_health():
    try:
        conn = db.get_connection()
        conn.execute("SELECT 1")
        memory = psutil.virtual_memory().percent
        return jsonify({
            "status": "healthy",
            "uptime": f"{(datetime.utcnow() - psutil.boot_time()).total_seconds() / 3600:.2f}h",
            "memory_usage": f"{memory}%",
            "components": {
                "db": "OK",
                "telegram": "Ready" if config.TELEGRAM_BOT_TOKEN else "Missing"
            }
        })
    except Exception as e:
        logger.critical(f"Secure health check failed: {str(e)}")
        abort(500)

# ========== DONE ==========


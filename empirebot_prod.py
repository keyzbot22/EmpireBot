from gevent import monkey
monkey.patch_all(ssl=False)

import os
import json
import base64
import hmac
import hashlib
import logging
import time
import threading
import requests
import sqlite3
from datetime import datetime, timedelta
from queue import Queue

from flask import Flask, request, jsonify, abort
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from prometheus_flask_exporter import PrometheusMetrics
import bcrypt

# === Logging ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# === Config ===
class Config:
    def __init__(self):
        self.SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(32).hex())
        self.JWT_SECRET = os.getenv("JWT_SECRET", os.urandom(32).hex())
        self.ADMIN_USER = os.getenv("ADMIN_USER", "admin")
        self.ADMIN_PW_HASH = bcrypt.hashpw(os.getenv("ADMIN_PW", "ChangeMe!").encode("utf-8"), bcrypt.gensalt())
        self.SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")
        self.ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
        self.REDIS_URL = os.getenv("REDIS_URL", "")
        self.BOTS = {
            "empire": os.getenv("EMPIRE_BOT_TOKEN"),
            "zariah": os.getenv("ZARIAH_BOT_TOKEN"),
            "chatgpt": os.getenv("CHATGPT_BOT_TOKEN"),
            "deepseek": os.getenv("DEEPSEEK_BOT_TOKEN"),
        }

config = Config()

# === Flask App ===
app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = config.JWT_SECRET
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=15)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
jwt = JWTManager(app)

# === Rate Limiting ===
try:
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        storage_uri=config.REDIS_URL if config.REDIS_URL else "memory://",
        default_limits=["500/hour", "50/minute"] if config.REDIS_URL else ["200/hour", "20/minute"]
    )
except Exception as e:
    logger.error(f"Rate limiter setup failed: {e}")
    limiter = Limiter(app=app, key_func=get_remote_address, storage="memory://")

# === Metrics ===
metrics = PrometheusMetrics(app)
metrics.info("app_info", "EmpireBot Metrics", version="6.3.2")

# === Database ===
class Database:
    def __init__(self):
        self.conn = sqlite3.connect(os.getenv("DATABASE_URL", "empirebot.db"), check_same_thread=False)
        self._init_db()

    def _init_db(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                order_id TEXT UNIQUE,
                amount REAL,
                timestamp TEXT,
                fraud_score REAL
            )
        ''')

    def create_backup(self):
        name = f"empirebot_{datetime.now().strftime('%Y%m%d_%H%M')}.backup"
        self.conn.execute(f"VACUUM INTO '{name}'")

db = Database()

# === Bot Manager (Threaded Queue System) ===
class BotManager:
    def __init__(self):
        self.queues = {bot: Queue() for bot in config.BOTS}
        self._running = True
        self.thread = threading.Thread(target=self._process_queues, daemon=True)
        self.thread.start()

    def _send_message(self, bot, msg):
        if token := config.BOTS.get(bot):
            try:
                requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": msg["chat_id"], "text": msg["text"]},
                    timeout=3
                )
            except Exception as e:
                logger.error(f"Error sending via {bot}: {e}")

    def _process_queues(self):
        while self._running:
            try:
                for bot, queue in self.queues.items():
                    if not queue.empty():
                        msg = queue.get()
                        self._send_message(bot, msg)
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
                time.sleep(1)

    def stop(self):
        self._running = False
        self.thread.join()

bot_manager = BotManager()

# === Security ===
@app.before_request
def verify_shopify():
    if request.path.startswith("/shopify"):
        timestamp = request.headers.get("X-Shopify-Webhook-Timestamp")
        if not timestamp or abs(time.time() - float(timestamp)) > 300:
            abort(403)
        hmac_header = request.headers.get("X-Shopify-Hmac-Sha256", "")
        digest = base64.b64encode(
            hmac.new(config.SHOPIFY_API_SECRET.encode(), request.data, hashlib.sha256).digest()
        ).decode()
        if not hmac.compare_digest(digest, hmac_header):
            abort(403)

def admin_only(f):
    @jwt_required()
    def wrapper(*args, **kwargs):
        if not get_jwt().get("is_admin"):
            abort(403)
        return f(*args, **kwargs)
    return wrapper

# === Routes ===
@app.route("/")
def health():
    try:
        db.conn.execute("SELECT 1").fetchone()
        return jsonify({
            "status": "healthy",
            "version": "6.3.2",
            "rate_limiter": "redis" if "redis" in str(limiter.storage).lower() else "memory",
            "bot_thread": "active"
        })
    except Exception as e:
        return jsonify({"status": "error", "details": str(e)}), 500

@app.route("/admin/login", methods=["POST"])
@limiter.limit("5/minute")
def login():
    data = request.get_json()
    if data.get("username") == config.ADMIN_USER and bcrypt.checkpw(data.get("password", "").encode(), config.ADMIN_PW_HASH):
        token = create_access_token(identity=config.ADMIN_USER, additional_claims={"is_admin": True})
        return jsonify(token=token)
    abort(401)

@app.route("/shopify/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    order_id = data.get("id")
    amount = float(data.get("total_price", 0))
    fraud = 0.0
    if data.get("billing_address", {}).get("country") != data.get("shipping_address", {}).get("country"):
        fraud += 0.3
    if amount > 5000:
        fraud += 0.4
    try:
        db.conn.execute(
            "INSERT INTO orders (order_id, amount, timestamp, fraud_score) VALUES (?, ?, ?, ?)",
            (order_id, amount, datetime.utcnow().isoformat(), fraud)
        )
    except sqlite3.IntegrityError:
        return jsonify(status="duplicate"), 200
    bot_manager.queues["empire"].put({
        "chat_id": config.ADMIN_CHAT_ID,
        "text": f"💰 Order: ${amount:.2f} | Risk: {fraud:.0%}"
    })
    return jsonify(status="processed")

@app.route("/bot/send", methods=["POST"])
@admin_only
def send_msg():
    data = request.get_json()
    bot = data.get("bot")
    if bot in bot_manager.queues:
        bot_manager.queues[bot].put({
            "chat_id": data.get("chat_id", config.ADMIN_CHAT_ID),
            "text": data["text"]
        })
        return jsonify(status="queued")
    abort(400)

@app.errorhandler(Exception)
def handle_error(e):
    logger.error(f"Unhandled exception: {e}")
    return jsonify(error=str(e)), 500

# === Run ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

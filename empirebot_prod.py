from gevent import monkey
monkey.patch_all(ssl=False)

import os
import json
import base64
import hmac
import hashlib
import logging
import threading
import asyncio
import bcrypt
import sqlite3
import time
import flask
import aiohttp
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt
from prometheus_flask_exporter import PrometheusMetrics

# Version check
assert flask.__version__.startswith("2."), f"❌ Flask 2.x required, found {flask.__version__}"

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# === Config ===
class Config:
    def __init__(self):
        self.SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(32).hex())
        self.JWT_SECRET = os.getenv("JWT_SECRET", os.urandom(32).hex())
        self.ADMIN_USER = os.getenv("ADMIN_USER")
        self.ADMIN_PW_HASH = bcrypt.hashpw(os.getenv("ADMIN_PW", "ChangeMe!").encode("utf-8"), bcrypt.gensalt())
        self.SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")
        self.ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
        self.REDIS_URL = os.getenv("REDIS_URL")
        self.BOTS = {
            "empire": os.getenv("EMPIRE_BOT_TOKEN"),
            "zariah": os.getenv("ZARIAH_BOT_TOKEN"),
            "chatgpt": os.getenv("CHATGPT_BOT_TOKEN"),
            "deepseek": os.getenv("DEEPSEEK_BOT_TOKEN")
        }

config = Config()

# === Flask Setup ===
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = config.JWT_SECRET
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
app.config['JWT_COOKIE_SECURE'] = True
app.config['JWT_COOKIE_CSRF_PROTECT'] = True
jwt = JWTManager(app)

# === Rate Limiting (with fallback) ===
try:
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        storage_uri=config.REDIS_URL if config.REDIS_URL else "memory://",
        strategy="moving-window",
        default_limits=["500/hour", "50/minute"] if config.REDIS_URL else ["200/hour", "20/minute"]
    )
except Exception as e:
    logger.error(f"Rate limiter setup failed: {e}")
    limiter = Limiter(app=app, key_func=get_remote_address, storage="memory://")

# === Metrics ===
metrics = PrometheusMetrics(app)
metrics.info("app_info", "EmpireBot v6.3.1", version="6.3.1")
bot_messages = metrics.counter("bot_messages_total", "Total bot messages sent", labels={"bot": lambda: request.json.get("bot")})

# === DB ===
class Database:
    def __init__(self):
        self.conn = sqlite3.connect(os.getenv("DATABASE_URL", "empirebot.db"), check_same_thread=False)
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                order_id TEXT UNIQUE,
                amount REAL,
                timestamp TEXT,
                fraud_score REAL
            )
        """)

    def create_backup(self):
        backup_name = f"empirebot_{datetime.now().strftime('%Y%m%d_%H%M')}.backup"
        self.conn.execute(f"VACUUM INTO '{backup_name}'")
        if os.getenv("AWS_BUCKET"):
            import boto3
            s3 = boto3.client("s3")
            s3.upload_file(backup_name, os.getenv("AWS_BUCKET"), backup_name)

db = Database()

# === Bot Manager ===
class BotManager:
    def __init__(self, loop):
        self.loop = loop
        self.queues = {bot: asyncio.Queue() for bot in config.BOTS}
        self.session = aiohttp.ClientSession(loop=loop)

    async def run_forever(self):
        while True:
            try:
                await self.process_queues()
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Bot manager error: {e}")
                await asyncio.sleep(1)

    async def process_queues(self):
        for bot, queue in self.queues.items():
            if not queue.empty():
                msg = await queue.get()
                await self.send_message(bot, msg)

    async def send_message(self, bot, msg):
        if token := config.BOTS.get(bot):
            try:
                async with self.session.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": msg["chat_id"], "text": msg["text"]},
                    timeout=3
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"Bot {bot} failed: {await resp.text()}")
            except Exception as e:
                logger.error(f"Error sending via {bot}: {e}")

manager = None

def start_bots():
    def run():
        global manager
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        manager = BotManager(loop)
        try:
            loop.run_until_complete(manager.run_forever())
        finally:
            loop.run_until_complete(manager.session.close())
            loop.close()

    threading.Thread(target=run, daemon=True).start()

# === Security ===
@app.before_request
def verify_shopify():
    if request.path.startswith("/shopify"):
        timestamp = request.headers.get("X-Shopify-Webhook-Timestamp")
        if not timestamp or abs(time.time() - float(timestamp)) > 300:
            abort(403)
        hmac_header = request.headers.get("X-Shopify-Hmac-Sha256", "")
        digest = base64.b64encode(hmac.new(config.SHOPIFY_API_SECRET.encode(), request.data, hashlib.sha256).digest()).decode()
        if not hmac.compare_digest(digest, hmac_header):
            abort(403)

def admin_only(f):
    @wraps(f)
    @jwt_required()
    def wrapper(*args, **kwargs):
        if not get_jwt().get("is_admin"):
            abort(403)
        return f(*args, **kwargs)
    return wrapper

# === Routes ===
@app.route("/")
def health_check():
    return jsonify({
        "status": "healthy",
        "version": "6.3.1",
        "rate_limiter": "redis" if "redis" in str(limiter.storage).lower() else "memory",
        "bot_thread": "active"
    })

@app.route("/admin/login", methods=["POST"])
@limiter.limit("5/minute")
def login():
    data = request.get_json()
    if data.get("username") == config.ADMIN_USER and bcrypt.checkpw(data.get("password", "").encode("utf-8"), config.ADMIN_PW_HASH):
        return jsonify(token=create_access_token(identity=config.ADMIN_USER, additional_claims={"is_admin": True}))
    abort(401)

@app.route("/shopify/webhook", methods=["POST"])
def shopify_webhook():
    data = request.get_json()
    order_id = data.get("id")
    amount = float(data.get("total_price", 0))
    fraud_score = 0.0
    if data.get("billing_address", {}).get("country") != data.get("shipping_address", {}).get("country"):
        fraud_score += 0.3
    if amount > 5000:
        fraud_score += 0.4
    try:
        db.conn.execute("INSERT INTO orders (order_id, amount, timestamp, fraud_score) VALUES (?, ?, ?, ?)",
                        (order_id, amount, datetime.utcnow().isoformat(), fraud_score))
    except sqlite3.IntegrityError:
        return jsonify(status="duplicate"), 200
    asyncio.run(manager.queues["empire"].put({"chat_id": config.ADMIN_CHAT_ID, "text": f"💰 Order: ${amount:.2f} | Risk: {fraud_score:.0%}"}))
    return jsonify(status="processed")

@app.route("/bot/send", methods=["POST"])
@admin_only
def send_bot_message():
    data = request.get_json()
    bot_messages.inc()
    asyncio.run(manager.queues[data.get("bot", "empire")].put({
        "chat_id": data.get("chat_id", config.ADMIN_CHAT_ID),
        "text": data["text"]
    }))
    return jsonify(status="sent")

@app.errorhandler(Exception)
def handle_errors(e):
    logger.error(f"Unhandled exception: {str(e)}")
    return jsonify(error=str(e)), 500

# === Boot ===
if __name__ == "__main__":
    start_bots()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
else:
    start_bots()


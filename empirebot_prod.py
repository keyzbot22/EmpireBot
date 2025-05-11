# EmpireBot v6.3 - Ultimate E-Commerce Automation (4-Bot Final)
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
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, abort
from flask_limiter import Limiter
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt
from dotenv import load_dotenv
import aiohttp

# ========== SETUP ==========
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ========== CONFIG ==========
class Config:
    def __init__(self):
        self.SECRET_KEY = os.getenv('SECRET_KEY')
        self.JWT_SECRET = os.getenv('JWT_SECRET')
        self.ADMIN_USER = os.getenv('ADMIN_USER')
        self.ADMIN_PW_HASH = bcrypt.hashpw(
            os.getenv('ADMIN_PW', 'ChangeMe!').encode('utf-8'),
            bcrypt.gensalt()
        )
        self.SHOPIFY_API_SECRET = os.getenv('SHOPIFY_API_SECRET')
        self.ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
        self.BOTS = {
            'empire': os.getenv('EMPIRE_BOT_TOKEN'),
            'zariah': os.getenv('ZARIAH_BOT_TOKEN'),
            'chatgpt': os.getenv('CHATGPT_BOT_TOKEN'),
            'deepseek': os.getenv('DEEPSEEK_BOT_TOKEN')
        }
        if not self.SECRET_KEY or not self.JWT_SECRET:
            raise ValueError("Missing critical environment variables")

config = Config()

# ========== APP ==========
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = config.JWT_SECRET
jwt = JWTManager(app)
limiter = Limiter(app, key_func=lambda: 'global', default_limits=["200/day"])

# ========== DATABASE ==========
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('empirebot.db', check_same_thread=False)
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                order_id TEXT UNIQUE,
                amount REAL,
                timestamp TEXT,
                fraud_score REAL
            )
        ''')

    def insert_order(self, order_id, amount, timestamp, fraud_score):
        self.conn.execute(
            'INSERT INTO orders (order_id, amount, timestamp, fraud_score) VALUES (?, ?, ?, ?)',
            (order_id, amount, timestamp, fraud_score)
        )
        self.conn.commit()

db = Database()

# ========== BOTS ==========
class BotManager:
    def __init__(self):
        self.queues = {bot: asyncio.Queue() for bot in config.BOTS}

    async def process_messages(self):
        while True:
            for bot, queue in self.queues.items():
                if not queue.empty():
                    msg = await queue.get()
                    await self._send_async(bot, msg['chat_id'], msg['text'])
            await asyncio.sleep(0.1)

    async def _send_async(self, bot, chat_id, text):
        token = config.BOTS.get(bot)
        if not token:
            return
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f'https://api.telegram.org/bot{token}/sendMessage',
                    json={'chat_id': chat_id, 'text': text},
                    timeout=5
                )
        except Exception as e:
            logger.error(f'Bot {bot} error: {e}')

bot_manager = BotManager()

# ========== HELPERS ==========
def calculate_fraud_score(data):
    score = 0.0
    if data.get('billing_address', {}).get('country') != data.get('shipping_address', {}).get('country'):
        score += 0.3
    if float(data.get('total_price', 0)) > 5000:
        score += 0.4
    return score

def start_bots():
    def run():
        asyncio.run(bot_manager.process_messages())
    threading.Thread(target=run, daemon=True).start()

# ========== SECURITY ==========
@app.before_request
def verify_shopify():
    if request.path.startswith('/shopify'):
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256', '')
        digest = base64.b64encode(hmac.new(
            config.SHOPIFY_API_SECRET.encode(),
            request.data,
            hashlib.sha256
        ).digest()).decode()
        if not hmac.compare_digest(digest, hmac_header):
            abort(403)

def admin_only(f):
    @wraps(f)
    @jwt_required()
    def wrapper(*args, **kwargs):
        if not get_jwt().get('is_admin'):
            abort(403)
        return f(*args, **kwargs)
    return wrapper

# ========== ROUTES ==========
@app.route('/admin/login', methods=['POST'])
@limiter.limit("5/minute")
def login():
    data = request.get_json()
    if (data.get('username') == config.ADMIN_USER and
        bcrypt.checkpw(data.get('password', '').encode('utf-8'), config.ADMIN_PW_HASH)):
        return jsonify(token=create_access_token(
            identity=config.ADMIN_USER,
            additional_claims={'is_admin': True}
        ))
    abort(401)

@app.route('/shopify/webhook', methods=['POST'])
def shopify_webhook():
    data = request.get_json()
    order_id = data.get('id')
    amount = float(data.get('total_price', 0))
    fraud_score = calculate_fraud_score(data)

    try:
        db.insert_order(order_id, amount, datetime.utcnow().isoformat(), fraud_score)
    except sqlite3.IntegrityError:
        return jsonify(status='duplicate'), 200

    bot = 'zariah' if fraud_score < 0.5 else 'empire'
    asyncio.run(bot_manager.queues[bot].put({
        'chat_id': config.ADMIN_CHAT_ID,
        'text': f'💰 New Order: ${amount:.2f} | Fraud Risk: {fraud_score:.0%}'
    }))

    return jsonify(status='processed')

@app.route('/bot/send', methods=['POST'])
@admin_only
def send_bot_message():
    data = request.get_json()
    if (bot := data.get('bot')) not in config.BOTS:
        abort(400)
    asyncio.run(bot_manager.queues[bot].put({
        'chat_id': data.get('chat_id', config.ADMIN_CHAT_ID),
        'text': data['text']
    }))
    return jsonify(status='sent')

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify(status='ok', timestamp=datetime.utcnow().isoformat())

# ========== STARTUP ==========
if __name__ == '__main__':
    start_bots()
    app.run(host='0.0.0.0', port=5000)

from gevent import monkey
monkey.patch_all(ssl=False, thread=False)

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

from flask import Flask, request, jsonify, abort, render_template
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from prometheus_flask_exporter import PrometheusMetrics

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
        self.ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
        self.REDIS_URL = os.getenv('REDIS_URL')
        self.BOTS = {
            'empire': os.getenv('EMPIRE_BOT_TOKEN'),
            'zariah': os.getenv('ZARIAH_BOT_TOKEN'),
            'chatgpt': os.getenv('CHATGPT_BOT_TOKEN'),
            'deepseek': os.getenv('DEEPSEEK_BOT_TOKEN')
        }

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
    if config.REDIS_URL and config.REDIS_URL.startswith("redis://"):
        from redis import Redis
        redis_client = Redis.from_url(config.REDIS_URL)
        redis_client.ping()
        limiter = Limiter(app=app, key_func=get_remote_address, storage_uri=config.REDIS_URL, strategy="moving-window", default_limits=["500/hour", "50/minute"])
        logger.info("✅ Redis rate limiting enabled")
    else:
        raise ValueError("REDIS_URL missing or invalid")
except Exception as e:
    logger.warning(f"⚠️ Using in-memory rate limiting: {str(e)}")
    limiter = Limiter(app=app, key_func=get_remote_address, storage_uri="memory://", strategy="moving-window", default_limits=["200/hour", "20/minute"])

# === Metrics ===
metrics = PrometheusMetrics(app)
metrics.info('app_info', 'EmpireBot Metrics', version='6.3.2')

# === Database ===
class Database:
    def __init__(self):
        self.conn = sqlite3.connect(os.getenv('DATABASE_URL', 'empirebot.db'), check_same_thread=False)
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
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                source TEXT,
                link TEXT,
                due_date TEXT
            )
        ''')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS contract_alerts (
                id INTEGER PRIMARY KEY,
                contract_id INTEGER,
                alert_type TEXT,
                timestamp TEXT,
                FOREIGN KEY(contract_id) REFERENCES contracts(id)
            )
        ''')
        self.conn.commit()

    def safe_execute(self, query, params=()):
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            if query.strip().lower().startswith("select"):
                return cursor.fetchall()
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"DB Error: {e} | Query: {query}")
            return []

db = Database()

# === Bot Manager ===
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
                    f'https://api.telegram.org/bot{token}/sendMessage',
                    json={'chat_id': msg['chat_id'], 'text': msg['text']},
                    timeout=3
                )
            except Exception as e:
                logger.error(f'Bot Error [{bot}]: {e}')

    def _process_queues(self):
        while self._running:
            for bot, queue in self.queues.items():
                if not queue.empty():
                    msg = queue.get()
                    self._send_message(bot, msg)
            time.sleep(0.1)

bot_manager = BotManager()

# === Security ===
@app.before_request
def verify_shopify():
    if request.path.startswith('/shopify'):
        timestamp = request.headers.get('X-Shopify-Webhook-Timestamp')
        hmac_header = request.headers.get('X-Shopify-Hmac-Sha256', '')
        digest = base64.b64encode(hmac.new(config.SHOPIFY_API_SECRET.encode(), request.data, hashlib.sha256).digest()).decode()
        if not timestamp or abs(time.time() - float(timestamp)) > 300 or not hmac.compare_digest(digest, hmac_header):
            abort(403)

def admin_only(f):
    @wraps(f)
    @jwt_required()
    def wrapper(*args, **kwargs):
        if not get_jwt().get('is_admin'):
            abort(403)
        return f(*args, **kwargs)
    return wrapper

# === Routes ===
@app.route('/')
def health_check():
    return jsonify({
        "status": "running",
        "version": "6.3.2",
        "bot_thread": bot_manager.thread.is_alive(),
        "message_queues": {k: v.qsize() for k, v in bot_manager.queues.items()}
    })
from flask import send_file

@app.route('/admin/backup', methods=['POST'])
@admin_only
def backup_db():
    backup_file = f"backup-{datetime.now().date()}.db"
    os.system(f"sqlite3 empirebot.db .dump > {backup_file}")
    return send_file(backup_file, as_attachment=True)

@app.route('/contracts-dashboard')
def contracts_dashboard():
    try:
        contracts_scraped = db.conn.execute("SELECT COUNT(*) FROM contracts").fetchone()[0]
    except Exception:
        contracts_scraped = 0
    return jsonify({
        "current_stage": "Phase 1 - Data Harvesting",
        "contracts_scraped": contracts_scraped,
        "alerts": [],
        "next_steps": [
            "✅ SAM.gov registration in progress",
            "✅ WOSB checklist generated",
            "📄 First proposals generating"
        ],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })

@app.route('/contracts-panel')
def contracts_panel():
    try:
        contracts = db.conn.execute("""
            SELECT id, title, source, link, due_date 
            FROM contracts 
            WHERE source IS NOT NULL 
            ORDER BY due_date ASC 
            LIMIT 20
        """).fetchall()
    except Exception as e:
        logger.error(f"Contract panel error: {e}")
        contracts = []
    
    return render_template("contracts.html", 
                         contracts=contracts,
                         last_updated=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'))

# === Boot ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))




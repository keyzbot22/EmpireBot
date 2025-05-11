from flask import Flask, request, jsonify, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
import openai
import sqlite3
import os
import requests
from datetime import datetime
from functools import wraps
import threading
import time
import psutil
from sqlite3 import Error as DBError
from prometheus_client import start_http_server, Counter, Gauge
from queue import Queue, deque
from threading import Thread
from logging.handlers import RotatingFileHandler
from gevent import monkey
from hashlib import md5
import asyncio
import aiohttp
import json
import zlib
import base64

monkey.patch_all()

app = Flask(__name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app.config.update({
    'DATABASE': os.path.join(BASE_DIR, 'empirebot.db'),
    'RATE_LIMIT': "500 per day, 30 per minute",
    'BACKUP_INTERVAL_MINUTES': 60,
    'HEARTBEAT_URL': os.getenv('HEARTBEAT_PING_URL'),
    'ADMIN_CHAT_ID': os.getenv('TELEGRAM_CHAT_ID'),
    'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN'),
})

openai.api_key = os.getenv("OPENAI_API_KEY")

limiter = Limiter(app=app, key_func=get_remote_address, default_limits=[app.config['RATE_LIMIT']])
cache = Cache(config={'CACHE_TYPE': 'SimpleCache'})
cache.init_app(app)

REQUESTS = Counter('empirebot_requests', 'Endpoint calls')
ERRORS = Counter('empirebot_errors', 'API errors')
TOKENS = Gauge('empirebot_tokens', 'Tokens used')

handler = RotatingFileHandler('empirebot.log', maxBytes=1000000, backupCount=3)
handler.setLevel(logging.WARNING)
app.logger.addHandler(handler)

message_queue = Queue(maxsize=100)
write_queue = deque()
last_write = time.time()
blacklisted_ips = set()

async def telegram_worker():
    async with aiohttp.ClientSession() as session:
        while True:
            msg = message_queue.get()
            try:
                compressed = zlib.compress(json.dumps(msg).encode())
                await session.post(
                    f"https://api.telegram.org/bot{app.config['TELEGRAM_BOT_TOKEN']}/sendMessage",
                    data=base64.b64encode(compressed),
                    headers={'Content-Encoding': 'deflate'}
                )
            except Exception as e:
                app.logger.warning(f"Telegram send failed: {str(e)}")
            message_queue.task_done()

Thread(target=lambda: asyncio.run(telegram_worker()), daemon=True).start()
Thread(target=lambda: db_writer(), daemon=True).start()
Thread(target=lambda: db_maintenance(), daemon=True).start()

@app.before_request
def firewall():
    if request.remote_addr in blacklisted_ips:
        abort(403)
    load = psutil.cpu_percent() / 100 + psutil.virtual_memory().percent / 100
    if load > 1.5:
        limiter.enabled = False
        return jsonify({"error": "System busy"}), 503
    elif load > 1.0:
        limiter.limit = "30 per minute"
    else:
        limiter.limit = app.config['RATE_LIMIT']

def require_api_key(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if os.getenv("PRODUCTION") == "True":
            key = request.headers.get("X-API-KEY")
            if key != os.getenv("API_KEY"):
                return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return wrapper

def get_db():
    db = sqlite3.connect(app.config['DATABASE'], timeout=30, detect_types=sqlite3.PARSE_DECLTYPES, isolation_level=None)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous = NORMAL")
    db.execute("PRAGMA busy_timeout = 5000")
    db.execute("PRAGMA cache_size = -10000")
    return db

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS queries (id INTEGER PRIMARY KEY, timestamp TEXT, ip_address TEXT, query TEXT, response TEXT, tokens_used INTEGER)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS system_metrics (timestamp TEXT PRIMARY KEY, memory_usage REAL, cpu_load REAL, active_connections INTEGER)''')

def log_query(ip, query, response, tokens):
    write_queue.append((datetime.utcnow().isoformat(), ip, query, response, tokens))

def db_writer():
    global last_write
    while True:
        if write_queue and (len(write_queue) > 10 or time.time() - last_write > 5):
            batch = list(write_queue)
            write_queue.clear()
            try:
                with get_db() as conn:
                    conn.executemany("INSERT INTO queries VALUES (NULL, ?, ?, ?, ?, ?)", batch)
            except DBError as e:
                send_alert(f"DB Batch Error: {str(e)}")
            last_write = time.time()
        time.sleep(0.1)

def db_maintenance():
    while True:
        time.sleep(86400)
        with get_db() as conn:
            conn.execute("VACUUM")
            conn.execute("PRAGMA optimize")

def log_error(endpoint, msg):
    app.logger.error(f"[ERROR] {endpoint}: {msg}")
    ERRORS.inc()

def get_system_metrics():
    return {
        "memory": psutil.virtual_memory().percent,
        "cpu": psutil.cpu_percent(),
        "connections": len(psutil.net_connections()),
        "uptime": psutil.boot_time()
    }

def log_system_metrics():
    m = get_system_metrics()
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO system_metrics VALUES (?, ?, ?, ?)", (datetime.utcnow().isoformat(), m['memory'], m['cpu'], m['connections']))

def send_heartbeat():
    if app.config['HEARTBEAT_URL']:
        try:
            requests.get(app.config['HEARTBEAT_URL'], timeout=5)
        except:
            pass

@app.route('/ask_chatgpt', methods=['POST'])
@require_api_key
@limiter.limit(app.config['RATE_LIMIT'])
@cache.memoize(timeout=300)
def ask_chatgpt():
    REQUESTS.inc()
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    query = data.get("query", "").strip()
    query_hash = md5(query.encode()).hexdigest()
    priority = request.headers.get("X-Priority", "normal")

    if not query or len(query) > 1000:
        return jsonify({"error": "Invalid query length"}), 400

    if cache.get(query_hash):
        return cache.get(query_hash)

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You're EmpireBot. Respond concisely."},
                {"role": "user", "content": query}
            ],
            temperature=0.7,
            max_tokens=150,
            request_timeout=15
        )
        result = response.choices[0].message['content']
        tokens = response.usage.total_tokens
        TOKENS.set(tokens)
        log_query(get_remote_address(), query, result, tokens)
        response_json = jsonify({"response": result, "tokens_used": tokens})
        cache.set(query_hash, response_json)
        return response_json
    except Exception as e:
        log_error("ask_chatgpt", str(e))
        send_alert(f"ChatGPT Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    try:
        m = get_system_metrics()
        return jsonify({
            "status": "EmpireBot is alive ✅",
            "metrics": m,
            "version": "3.1",
            "time": datetime.utcnow().isoformat()
        })
    except Exception as e:
        log_error("health", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/metrics', methods=['GET'])
def metrics():
    return jsonify({
        "requests": REQUESTS._value.get(),
        "errors": ERRORS._value.get(),
        "tokens": TOKENS._value.get(),
        "queue_size": message_queue.qsize(),
        "db_queue": len(write_queue)
    })

def backup_db():
    try:
        date = datetime.now().strftime("%Y%m%d")
        backup_file = f"empirebot_backup_{date}.db"
        with open(app.config['DATABASE'], 'rb') as src:
            with open(backup_file, 'wb') as dst:
                dst.write(src.read())
        send_alert(f"✅ Backup completed: {backup_file}")
    except Exception as e:
        send_alert(f"🔴 Backup failed: {str(e)}")

def send_alert(msg):
    if app.config['TELEGRAM_BOT_TOKEN']:
        message_queue.put({
            "chat_id": app.config['ADMIN_CHAT_ID'],
            "text": msg[:4000],
            "parse_mode": "Markdown"
        })

if __name__ == "__main__":
    from gunicorn.app.wsgiapp import run

    init_db()
    log_system_metrics()
    start_http_server(8000)

    def run_scheduled_tasks():
        last_metrics = last_heartbeat = last_backup = time.time()
        while True:
            now = time.time()
            if now - last_heartbeat >= 300:
                send_heartbeat()
                last_heartbeat = now
            if now - last_metrics >= 900:
                log_system_metrics()
                last_metrics = now
            if datetime.now().hour == 3 and now - last_backup >= 86400:
                backup_db()
                last_backup = now
            time.sleep(1 - (time.time() - now))

    threading.Thread(target=run_scheduled_tasks, daemon=True).start()
    run()

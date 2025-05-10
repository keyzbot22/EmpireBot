from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import openai
import sqlite3
import os
import requests
from datetime import datetime
from functools import wraps
import threading
import schedule
import time
import psutil

# ===== SETUP =====
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

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[app.config['RATE_LIMIT']]
)

# ===== AUTH CHECK =====
def require_api_key(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if os.getenv("PRODUCTION") == "True":
            key = request.headers.get("X-API-KEY")
            if key != os.getenv("API_KEY"):
                return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return wrapper

# ===== DB INIT =====
def init_db():
    with sqlite3.connect(app.config['DATABASE']) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            ip_address TEXT,
            query TEXT,
            response TEXT,
            tokens_used INTEGER
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS system_metrics (
            timestamp TEXT PRIMARY KEY,
            memory_usage REAL,
            cpu_load REAL,
            active_connections INTEGER
        )''')

def log_query(ip, query, response, tokens):
    with sqlite3.connect(app.config['DATABASE']) as conn:
        conn.execute("INSERT INTO queries VALUES (NULL, ?, ?, ?, ?, ?)",
            (datetime.utcnow().isoformat(), ip, query, response, tokens))

def log_error(endpoint, msg):
    app.logger.error(f"[ERROR] {endpoint}: {msg}")

def get_system_metrics():
    return {
        "memory": psutil.virtual_memory().percent,
        "cpu": psutil.cpu_percent(),
        "connections": len(psutil.net_connections()),
        "uptime": psutil.boot_time()
    }

def log_system_metrics():
    m = get_system_metrics()
    with sqlite3.connect(app.config['DATABASE']) as conn:
        conn.execute("INSERT OR REPLACE INTO system_metrics VALUES (?, ?, ?, ?)",
            (datetime.utcnow().isoformat(), m['memory'], m['cpu'], m['connections']))

# ===== AI CHAT ENDPOINT =====
@app.route('/ask_chatgpt', methods=['POST'])
@require_api_key
@limiter.limit(app.config['RATE_LIMIT'])
def ask_chatgpt():
    try:
        data = request.get_json()
        query = data.get("query", "")
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": query}],
            max_tokens=150
        )
        result = response.choices[0].message['content']
        tokens = response.usage.total_tokens
        log_query(get_remote_address(), query, result, tokens)
        return jsonify({"response": result, "tokens_used": tokens})
    except Exception as e:
        log_error("ask_chatgpt", str(e))
        send_alert(f"ChatGPT Error: {e}")
        return jsonify({"error": str(e)}), 500

# ===== HEALTH CHECK =====
@app.route('/health', methods=['GET'])
def health():
    try:
        m = get_system_metrics()
        return jsonify({
            "status": "EmpireBot is alive ✅",
            "metrics": m,
            "version": "2.0",
            "time": datetime.utcnow().isoformat()
        })
    except Exception as e:
        log_error("health", str(e))
        return jsonify({"error": str(e)}), 500

# ===== ALERTS =====
def send_alert(msg):
    if app.config['TELEGRAM_BOT_TOKEN'] and app.config['ADMIN_CHAT_ID']:
        try:
            requests.post(
                f"https://api.telegram.org/bot{app.config['TELEGRAM_BOT_TOKEN']}/sendMessage",
                json={"chat_id": app.config['ADMIN_CHAT_ID'], "text": msg}
            )
        except Exception as e:
            log_error("telegram_alert", str(e))

# ===== HEARTBEAT =====
def send_heartbeat():
    if app.config['HEARTBEAT_URL']:
        try:
            requests.get(app.config['HEARTBEAT_URL'], timeout=5)
        except:
            pass

# ===== SCHEDULER =====
def run_scheduler():
    schedule.every(5).minutes.do(send_heartbeat)
    schedule.every(app.config['BACKUP_INTERVAL_MINUTES']).minutes.do(log_system_metrics)
    while True:
        schedule.run_pending()
        time.sleep(1)

# ===== START =====
if __name__ == "__main__":
    init_db()
    log_system_metrics()
    threading.Thread(target=run_scheduler, daemon=True).start()
    app.run(host="0.0.0.0", port=6006, threaded=True)


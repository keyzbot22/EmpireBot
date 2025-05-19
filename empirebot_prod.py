import os
import hmac
import hashlib
import base64
import subprocess
import json
from functools import lru_cache
from flask import Flask, request, current_app, jsonify
from alert_manager import AlertManager
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from send2trash import send2trash

# === INIT ===
app = Flask(__name__)
executor = ThreadPoolExecutor(10)

# === CONFIG ===
CLEANUP_CONFIG = {
    "Shopify_Logs": {
        "max_age_days": 7,
        "keep_min": 100,
        "match": ".log"
    },
    "TikTok_Raw": {
        "max_age_days": 2,
        "match": "render_*.mp4"
    },
    "Legal_Temp": {
        "max_age_hours": 48,
        "shred": True
    }
}

# === UTILS ===
@lru_cache(maxsize=1)
def get_shopify_secret():
    secret = os.getenv("SHOPIFY_SECRET")
    if not secret or len(secret) < 32:
        raise ValueError("Invalid SHOPIFY_SECRET configuration")
    return secret

@lru_cache(maxsize=1)
def get_mobile_token():
    token = os.getenv("EMPIREBOT_MOBILE_TOKEN")
    if not token or len(token) < 32:
        raise ValueError("Mobile token not properly configured")
    return token

def verify_shopify_hmac(body: bytes, hmac_header: str) -> bool:
    try:
        secret = get_shopify_secret()
        digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
        expected = base64.b64encode(digest).decode()
        return hmac.compare_digest(hmac_header, expected)
    except Exception:
        return False

# === GOOGLE DRIVE ===
def upload_to_drive(file_path, folder_id=None):
    creds = Credentials.from_authorized_user_file('credentials.json', ['https://www.googleapis.com/auth/drive'])
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [folder_id] if folder_id else []
    }
    media = MediaFileUpload(file_path)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return f"https://drive.google.com/file/d/{file.get('id')}/view"

# === CLEANUP ===
def clean_directory():
    try:
        for name, config in CLEANUP_CONFIG.items():
            folder = f"/EmpireBot/{name}"
            for file in os.listdir(folder):
                full_path = os.path.join(folder, file)
                if os.path.isfile(full_path):
                    age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(full_path))
                    if config.get("max_age_days") and age > timedelta(days=config["max_age_days"]):
                        if config.get("shred"):
                            send2trash(full_path)
                        else:
                            os.remove(full_path)
    except Exception as e:
        AlertManager().send(f"🧹 Cleanup failed: {e}")

# === ROUTES ===
@app.route('/')
def home():
    return "EmpireBot Mobile+Web is operational"

@app.route('/health')
def health():
    return jsonify({
        "status": "OK",
        "version": os.getenv("RELEASE_VERSION", "1.0.0"),
        "services": ["shopify", "mobile", "alerts"]
    })

@app.route('/bots/status')
def bot_status():
    return jsonify({
        "eBookGeneral": "Formatting AI Domination",
        "TikTokSpammer": "Rendering video",
        "ShopifyAIO": "Scanning new orders",
        "GovHunter": "RFP 92% done",
        "CryptoWolf": "Monitoring BTC",
        "LegalShark": "Drafting LLC",
        "GhostWriter": "Blog drafts queued"
    })

@app.route('/webhook/shopify/<webhook_type>', methods=['POST'])
def handle_webhook(webhook_type):
    return handle_shopify_webhook(webhook_type)

def handle_shopify_webhook(webhook_type: str):
    try:
        if not verify_shopify_hmac(request.get_data(), request.headers.get('X-Shopify-Hmac-Sha256', '')):
            current_app.logger.warning(f"Invalid HMAC attempt for {webhook_type}")
            return "Invalid HMAC", 403

        data = request.get_json(force=True)

        if webhook_type == "orders":
            AlertManager().send(f"🛒 New Order #{data['id']}\nTotal: ${data['total_price']}")
        elif webhook_type == "carts":
            AlertManager().send(f"🛍️ Cart activity: {data.get('email')}")
        elif webhook_type == "refunds":
            AlertManager().send(f"💸 Refund: Order #{data['order_id']}")
        elif webhook_type == "fulfillments":
            AlertManager().send(f"📦 Shipped: Order #{data['order_id']}")

        return "OK", 200

    except Exception as e:
        current_app.logger.error(f"{webhook_type} webhook failed: {str(e)}", exc_info=True)
        return "Processing error", 500

@app.route('/mobile/command', methods=['POST'])
def mobile_control():
    try:
        auth_token = request.headers.get('Authorization', '')
        if not hmac.compare_digest(auth_token, get_mobile_token()):
            current_app.logger.warning("Invalid mobile auth attempt")
            return "Unauthorized", 401

        command = request.json.get("action")
        params = request.json.get("params", {})

        if command == "status":
            return jsonify({
                "status": "operational",
                "bots": ["shopify", "alerts", "mobile"],
                "load": os.getloadavg()
            })

        elif command == "restart":
            subprocess.Popen(["/usr/bin/touch", "/tmp/restart.txt"])
            return jsonify({"status": "restart_scheduled"})

        elif command == "deploy":
            result = subprocess.run(["git", "pull"], capture_output=True, text=True)
            return jsonify({
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            })

        elif command == "clean":
            executor.submit(clean_directory)
            return jsonify({"status": "cleanup_started"})

        elif command == "set_env":
            if not isinstance(params, dict):
                return "Invalid params", 400
            with open("/tmp/latest_config.json", "w") as f:
                json.dump(params, f)
            return jsonify({"received_params": params})

        else:
            return "Unknown command", 400

    except Exception as e:
        current_app.logger.error(f"Mobile command failed: {str(e)}", exc_info=True)
        return "Command error", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5000)))

import os
import hmac
import hashlib
import base64
import subprocess
import json
from functools import lru_cache
from flask import Flask, request, current_app, jsonify
from alert_manager import AlertManager

# === INIT ===
app = Flask(__name__)

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

# === CORE ROUTES ===
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

# === SHOPIFY WEBHOOKS ===
def handle_shopify_webhook(webhook_type: str):
    try:
        if not verify_shopify_hmac(request.get_data(), request.headers.get('X-Shopify-Hmac-Sha256', '')):
            current_app.logger.warning(f"Invalid HMAC attempt for {webhook_type}")
            return "Invalid HMAC", 403

        data = request.get_json(force=True)

        if webhook_type == "orders":
            AlertManager().send(f"🛒 New Order #{data['id']}\nTotal: ${data['total_price']}")
            return "OK", 200

        elif webhook_type == "carts":
            AlertManager().send(f"🛍️ Cart activity: {data.get('email')}")
            return "OK", 200

        elif webhook_type == "refunds":
            AlertManager().send(f"💸 Refund: Order #{data['order_id']}")
            return "OK", 200

        elif webhook_type == "fulfillments":
            AlertManager().send(f"📦 Shipped: Order #{data['order_id']}")
            return "OK", 200

    except Exception as e:
        current_app.logger.error(f"{webhook_type} webhook failed: {str(e)}", exc_info=True)
        return "Processing error", 500

@app.route('/webhook/shopify/orders', methods=['POST'])
def order_webhook():
    return handle_shopify_webhook("orders")

@app.route('/webhook/shopify/carts', methods=['POST'])
def cart_webhook():
    return handle_shopify_webhook("carts")

@app.route('/webhook/shopify/refunds', methods=['POST'])
def refund_webhook():
    return handle_shopify_webhook("refunds")

@app.route('/webhook/shopify/fulfillments', methods=['POST'])
def fulfillment_webhook():
    return handle_shopify_webhook("fulfillments")

# === MOBILE COMMANDS ===
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



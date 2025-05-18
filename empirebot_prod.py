import os
import hmac
import hashlib
import base64
from functools import lru_cache
from flask import Flask, request, current_app
from alert_manager import AlertManager

# === INIT ===
app = Flask(__name__)

# === UTILS ===
@lru_cache(maxsize=1)
def get_shopify_secret():
    return os.getenv("SHOPIFY_SECRET")

def verify_shopify_hmac(body: bytes, hmac_header: str) -> bool:
    secret = get_shopify_secret()
    if not secret:
        raise ValueError("SHOPIFY_SECRET not configured")

    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(hmac_header, expected)

# === ROUTES ===
@app.route('/')
def home():
    return "EmpireBot is running successfully!"

@app.route('/health')
def health():
    return "OK"

@app.route('/test-alert')
def test_alert():
    try:
        alert = AlertManager()
        response = alert.send("🚨 Test alert from EmpireBot is working!")
        return f"Alert sent with status code: {response.status_code}"
    except Exception as e:
        return f"Alert failed: {str(e)}", 500

@app.route('/webhook/shopify/orders', methods=['POST'])
def handle_order_webhook():
    try:
        if not verify_shopify_hmac(request.get_data(), request.headers.get('X-Shopify-Hmac-Sha256', '')):
            return "Invalid HMAC", 403

        data = request.get_json(force=True)
        AlertManager().send(f"""
        🛒 New Order #{data['id']}
        Email: {data['email']}
        Total: ${data['total_price']}
        """)
        return "OK", 200

    except Exception as e:
        current_app.logger.error(f"Order webhook failed: {e}")
        return "Server Error", 500

@app.route('/webhook/shopify/carts', methods=['POST'])
def handle_cart_webhook():
    try:
        data = request.get_json(force=True)
        AlertManager().send(f"🛍️ Abandoned cart detected: {data.get('email')}")
        return "OK", 200
    except Exception as e:
        current_app.logger.error(f"Cart webhook failed: {e}")
        return "Server Error", 500

@app.route('/webhook/shopify/refunds', methods=['POST'])
def handle_refund_webhook():
    try:
        if not verify_shopify_hmac(request.get_data(), request.headers.get('X-Shopify-Hmac-Sha256', '')):
            return "Invalid HMAC", 403

        data = request.get_json(force=True)
        AlertManager().send(f"💸 Refund issued for order #{data['order_id']} — Reason: {data.get('note', 'N/A')}")
        return "OK", 200
    except Exception as e:
        current_app.logger.error(f"Refund webhook failed: {e}")
        return "Server Error", 500

@app.route('/webhook/shopify/fulfillments', methods=['POST'])
def handle_fulfillment_webhook():
    try:
        if not verify_shopify_hmac(request.get_data(), request.headers.get('X-Shopify-Hmac-Sha256', '')):
            return "Invalid HMAC", 403

        data = request.get_json(force=True)
        AlertManager().send(f"📦 Fulfilled: Order #{data['order_id']} shipped to {data.get('destination', {}).get('address1')}")
        return "OK", 200
    except Exception as e:
        current_app.logger.error(f"Fulfillment webhook failed: {e}")
        return "Server Error", 500


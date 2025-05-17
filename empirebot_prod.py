import os
import sys

# Ensure root directory is in the Python path for reliable imports on Render
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# DEBUGGING (optional - remove after confirming it works)
print("Current working directory:", os.getcwd())
print("Files in root:", os.listdir(current_dir))
print("alerts folder exists:", os.path.exists(os.path.join(current_dir, "alerts")))

from flask import Flask, request, jsonify
from alerts.manager import AlertManager  # ✅ make sure alerts/manager.py exists and has AlertManager

app = Flask(__name__)
alert_manager = AlertManager()

@app.route("/")
def index():
    return "EmpireBot is Live"

@app.route("/alerts", methods=["POST"])
def handle_alert():
    try:
        data = request.get_json()
        alert_manager.process(data)
        return jsonify({"status": "alert received"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Healthcheck route for Render and uptime monitors
@app.route("/health", methods=["GET"])
def healthcheck():
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

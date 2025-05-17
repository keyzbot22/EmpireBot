import os
import sys

# === DEBUG OUTPUT FOR RENDER DEPLOY ===
print("=== DEBUG INFO ===")
print("Current directory:", os.getcwd())
print("Directory contents:", os.listdir('.'))
print("alerts exists?", os.path.exists('alerts'))
if os.path.exists('alerts'):
    print("alerts contents:", os.listdir('alerts'))

# Add current directory to Python path for imports to work on Render
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Imports
from flask import Flask
from alerts.manager import AlertManager

# App + AlertManager setup
app = Flask(__name__)
alert_manager = AlertManager()

# Root route
@app.route('/')
def home():
    return "EmpireBot is running successfully!"

# Health check route
@app.route('/health', methods=['GET'])
def healthcheck():
    return "OK", 200

# Placeholder for future alert webhook
# @app.route('/alerts', methods=['POST'])
# def handle_alert():
#     data = request.get_json()
#     alert_manager.process(data)
#     return jsonify({"status": "processed"}), 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

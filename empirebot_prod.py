import os
import sys

# === DEBUG OUTPUT ===
print("=== DEBUG INFO ===")
print("Current directory:", os.getcwd())
print("Directory contents:", os.listdir('.'))
print("alerts exists?", os.path.exists('alerts'))
if os.path.exists('alerts'):
    print("alerts contents:", os.listdir('alerts'))

# Ensure root directory is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import your alert manager
from alerts.manager import AlertManager
from flask import Flask

# Initialize Flask app and alert manager
app = Flask(__name__)
alert_manager = AlertManager()

# Basic status route
@app.route('/')
def home():
    return "EmpireBot is running successfully!"

# (Optional) Add /healthcheck route
@app.route('/health', methods=['GET'])
def healthcheck():
    return "OK", 200

# (Optional placeholder for future logic)
# @app.route('/alerts', methods=['POST'])
# def handle_alert():
#     data = request.get_json()
#     alert_manager.process(data)
#     return jsonify({"status": "processed"}), 200

if __name__ == '__main__':
    app.run()

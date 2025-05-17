import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from prometheus_flask_exporter import PrometheusMetrics

# Add root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from alerts.manager import AlertManager
except ImportError:
    from .alerts.manager import AlertManager

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET', 'secret')
jwt = JWTManager(app)
metrics = PrometheusMetrics(app)

limiter = Limiter(app=app, key_func=get_remote_address)

alert_manager = AlertManager()

@app.route("/")
def index():
    return jsonify({"status": "running", "timestamp": datetime.utcnow().isoformat()})

@app.route("/test-alerts", methods=["GET"])
def test_alerts():
    message = f"🚨 EmpireBot Test at {datetime.now().isoformat()}"
    result = alert_manager.send(message)
    return jsonify(result)


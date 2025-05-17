import os
import sys

# === DEBUG OUTPUT FOR RENDER ===
print("=== DEBUG INFO ===")
print("Current directory:", os.getcwd())
print("Directory contents:", os.listdir('.'))
print("Parent directory contents:", os.listdir('..'))

# Add both current and parent directories to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try importing AlertManager from alert_manager.py (root-level)
try:
    from alert_manager import AlertManager
    print("✅ Successfully imported AlertManager")
except ImportError as e:
    print(f"❌ ImportError (AlertManager): {e}")
    print("sys.path:", sys.path)

# === FLASK APP ===
from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "EmpireBot is live with no import errors!"

@app.route('/health')
def health():
    return "OK"

if __name__ == '__main__':
    app.run()

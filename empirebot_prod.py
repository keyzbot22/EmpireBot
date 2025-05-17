import os
import sys

# === DEBUG OUTPUT FOR RENDER ===
print("=== DEBUG INFO ===")
print("Current directory:", os.getcwd())
print("Directory contents:", os.listdir('.'))
print("Parent directory contents:", os.listdir('..'))

# Add current and parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import AlertManager directly from root-level module
try:
    from alert_manager import AlertManager
    print("✅ Successfully imported AlertManager")
except ImportError as e:
    print(f"❌ ImportError: {e}")
    print("sys.path:", sys.path)

# === FLASK APP SETUP ===
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "EmpireBot is running successfully!"

@app.route('/health')
def health():
    return "OK"

if __name__ == '__main__':
    app.run()

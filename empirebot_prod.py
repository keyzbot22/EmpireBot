import os
import sys

# === DEBUG OUTPUT ===
print("=== DEBUG INFO ===")
print("Current directory:", os.getcwd())
print("Directory contents:", os.listdir('.'))

parent_dir = os.path.dirname(os.getcwd())
print("Parent directory contents:", os.listdir(parent_dir))

# === PATH FIXES ===
sys.path.insert(0, os.path.abspath('.'))  # Current dir
sys.path.insert(0, os.path.abspath('..'))  # Parent dir

# === MODULE IMPORT ===
try:
    from alerts.manager import AlertManager
    print("✅ Successfully imported AlertManager")
except ImportError as e:
    print("❌ ImportError:", e)
    print("sys.path:", sys.path)

# === FLASK APP ===
from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ EmpireBot is running!"

@app.route('/health')
def health():
    return {"status": "ok"}

if __name__ == '__main__':
    app.run()

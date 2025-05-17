import os
import sys

print("=== DEBUG INFO ===")
print("Current directory:", os.getcwd())
print("Directory contents:", os.listdir('.'))
print("alerts exists?", os.path.exists('alerts'))
if os.path.exists('alerts'):
    print("alerts contents:", os.listdir('alerts'))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from alerts.manager import AlertManager
from flask import Flask

app = Flask(__name__)
alert_manager = AlertManager()

@app.route('/')
def home():
    return "EmpireBot is running successfully!"

if __name__ == '__main__':
    app.run()

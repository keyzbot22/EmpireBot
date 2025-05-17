import os
import sys

# Debugging output
print("Current directory:", os.getcwd())
print("Directory contents:", os.listdir('.'))
print("alerts exists?", os.path.exists('alerts'))
print("alerts contents:", os.listdir('alerts') if os.path.exists('alerts') else "N/A")

# Ensure root directory is on Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Imports
from alerts.manager import AlertManager
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "EmpireBot is running!"

if __name__ == '__main__':
    app.run()

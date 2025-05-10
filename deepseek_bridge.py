from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

CHATGPT_API_KEY = os.getenv("CHATGPT_API_KEY")
API_SECRET = os.getenv("API_SECRET", "KeyzEmpire2024")

@app.before_request
def check_secret():
    if request.endpoint != 'status':
        if request.headers.get("X-API-SECRET") != API_SECRET:
            return jsonify({"error": "Unauthorized"}), 401

@app.route('/status')
def status():
    return jsonify({"status": "running"})

@app.route('/ask_chatgpt', methods=['POST'])
def ask_chatgpt():
    data = request.json
    headers = {
        "Authorization": f"Bearer {CHATGPT_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "You give powerful quotes about money and mindset."},
            {"role": "user", "content": data["query"]}
        ]
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return jsonify(response.json())

if __name__ == '__main__':
    app.run(port=6006)


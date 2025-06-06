# deepseek_ai.py

from flask import Flask, request, jsonify
import random
from datetime import datetime

app = Flask(__name__)

@app.route('/scan', methods=['POST'])
def scan():
    data = request.json
    symbol = data.get('symbol', 'BTC')

    # Simulate scan logic
    result = {
        "symbol": symbol,
        "action": "BUY" if random.random() > 0.5 else "SELL",
        "confidence": round(random.uniform(0.7, 0.95), 2),
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    print(f"[DEBUG] Scan result: {result}")
    return jsonify(result)

if __name__ == '__main__':
    app.run(port=8051, debug=True)


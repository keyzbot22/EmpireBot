import os
import requests

print("✅ Testing Trade Log (simulated)...")
log_path = 'logs/trades.log'
os.makedirs('logs', exist_ok=True)
with open(log_path, 'w') as f:
    f.write("[2025-06-04 18:17] Trade executed: BUY 0.01 BTC @ $68,420.50 (Coinbase)\n")
print("✔️ Trade logged.")

print("🔍 Testing DeepSeek Scan...")
resp = requests.post("http://localhost:8051/scan", json={"symbol": "BTC"})
print("DeepSeek response:", resp.json())

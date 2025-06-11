from fastapi import FastAPI, Request
import random
from datetime import datetime

app = FastAPI()

@app.post("/scan")
async def scan(request: Request):
    data = await request.json()
    return {
        'symbol': data.get('symbol', 'BTC').upper(),
        'action': random.choice(['BUY', 'SELL']),
        'confidence': round(random.uniform(0.7, 0.95), 2),
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

@app.get("/health")
async def health():
    return {"status": "online"}

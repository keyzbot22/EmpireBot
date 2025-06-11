from fastapi import FastAPI, Request
from datetime import datetime
import random

app = FastAPI()

@app.post("/scan")
async def scan(request: Request):
    body = await request.json()
    symbol = body.get("symbol", "BTC").upper()

    action = random.choice(["BUY", "SELL", "HOLD"])
    confidence = round(random.uniform(0.7, 0.99), 2)

    return {
        "symbol": symbol,
        "action": action,
        "confidence": confidence,
        "timestamp": datetime.utcnow().isoformat()
    }


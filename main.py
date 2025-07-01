from fastapi import FastAPI
from prometheus_client import make_asgi_app, Counter, Gauge
import os, httpx
from datetime import datetime
from telegram import Bot

app = FastAPI()
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

REQUEST_COUNT = Counter('app_requests_total', 'Total HTTP Requests')
HEALTH_CHECK_GAUGE = Gauge('app_health_status', 'Health check status')

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
MONITOR_URL = os.getenv("MONITOR_URL")

@app.on_event("startup")
async def startup_event():
    await notify_deploy("🚀 EmpireBot deployment started")

@app.get("/health")
async def health():
    HEALTH_CHECK_GAUGE.set(1)
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "v1"
    }

@app.get("/")
async def root():
    REQUEST_COUNT.inc()
    return {"message": "EmpireBot is running!"}

async def notify_deploy(msg: str):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)

async def verify_uptime():
    if MONITOR_URL:
        async with httpx.AsyncClient() as client:
            try:
                await client.get(f"{MONITOR_URL}/health")
            except Exception as e:
                await notify_deploy(f"⚠️ Uptime check failed: {str(e)}")


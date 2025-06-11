import os
import nest_asyncio
import asyncio
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, AIORateLimiter

nest_asyncio.apply()

TOKEN = os.getenv("ZARIAH_BOT_TOKEN")
APP_URL = os.getenv("RAILWAY_WEBHOOK_URL")  # Ex: https://skillful-energy.up.railway.app
WEBHOOK_SECRET = "zariah-secret"
WEBHOOK_PATH = f"/zariah/{WEBHOOK_SECRET}"

app = FastAPI()
telegram_app = Application.builder().token(TOKEN).rate_limiter(AIORateLimiter()).build()

# === Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 ZariahBot Activated!")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ ZariahBot is online!")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("status", status))

# === Webhook route ===
@app.post(WEBHOOK_PATH)
async def webhook_handler(request: Request):
    data = await request.json()
    await telegram_app.update_queue.put(Update.de_json(data, telegram_app.bot))
    return {"ok": True}

# === Health Check ===
@app.get("/health")
async def health():
    return {"status": "online"}

# === On Startup, Register Webhook ===
@app.on_event("startup")
async def on_startup():
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(url=APP_URL + WEBHOOK_PATH)
    print("✅ Webhook set to:", APP_URL + WEBHOOK_PATH)




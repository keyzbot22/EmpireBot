import nest_asyncio
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.ext import AIORateLimiter
from fastapi import FastAPI, Request
import os

# Setup
nest_asyncio.apply()
TOKEN = os.getenv("ZARIAH_BOT_TOKEN") or "7329634509:AAG2sydFNeF02HuNYV8L9fDDXZViecXa7uA"
WEBHOOK_SECRET = "zariah-secret"
WEBHOOK_PATH = f"/zariah/{WEBHOOK_SECRET}"
APP_URL = os.getenv("RAILWAY_WEBHOOK_URL") or "https://skillful-energy.up.railway.app"

# FastAPI app
app = FastAPI()
telegram_app = Application.builder().token(TOKEN).rate_limiter(AIORateLimiter()).build()

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    await update.message.reply_text("🤖 ZariahBot Activated!")
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    await update.message.reply_text("✅ System Status: Online")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("status", status))

# FastAPI route for webhook
@app.post(WEBHOOK_PATH)
async def handle_update(request: Request):
    data = await request.json()
    await telegram_app.update_queue.put(Update.de_json(data, telegram_app.bot))
    return {"ok": True}

# Startup event to set webhook
@app.on_event("startup")
async def startup():
    await telegram_app.bot.set_webhook(url=APP_URL + WEBHOOK_PATH)
    print("🚀 ZariahBot webhook set!")





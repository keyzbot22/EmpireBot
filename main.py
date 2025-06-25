import asyncio
import logging
from fastapi import FastAPI
from datetime import datetime
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update
import os

# === Setup ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
app = FastAPI()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# === FastAPI Health Check ===
@app.get("/health")
def health():
    return {"status": "alive", "timestamp": datetime.now().isoformat()}

# === Telegram Commands ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 ZariahBot is live and trading!")

async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = " ".join(context.args)
    await update.message.reply_text(f"⏰ Reminder set: {msg}")

async def alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = " ".join(context.args)
    await update.message.reply_text(f"📊 Alert saved: {msg}")

async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = " ".join(context.args)
    await update.message.reply_text(f"💹 Trade command received: {msg}")

async def send_vendor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = " ".join(context.args)
    await update.message.reply_text(f"📧 Vendor message queued: {msg}")

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📆 Daily report task triggered.")

async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📤 Upload started.")

# === Telegram Bot Runner ===
async def run_bot():
    app_builder = ApplicationBuilder().token(BOT_TOKEN)
    application = app_builder.build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("remind", remind))
    application.add_handler(CommandHandler("alert", alert))
    application.add_handler(CommandHandler("trade", trade))
    application.add_handler(CommandHandler("send_vendor", send_vendor))
    application.add_handler(CommandHandler("daily", daily))
    application.add_handler(CommandHandler("upload", upload))

    logger.info("✅ ZariahBot Telegram is live.")
    await application.run_polling()

# === Entrypoint for Uvicorn + Asyncio ===
@app.on_event("startup")
async def on_startup():
    asyncio.create_task(run_bot())


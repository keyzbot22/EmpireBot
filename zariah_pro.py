import os
import logging
import asyncio
from fastapi import FastAPI
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram import Update
from telegram.ext import ContextTypes

# Load .env variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not BOT_TOKEN:
    raise EnvironmentError("Missing required environment variable: TELEGRAM_TOKEN")

# Logging setup
logging.basicConfig(
    format="%(asctime)s - ZariahBot - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Telegram command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ZariahBot is live and operational! 🚀")

# Build Telegram bot app
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))

# FastAPI app (optional, you can remove this if you’re not using the API side)
app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/metrics")
async def metrics():
    return {"trades_executed": 0, "alerts_sent": 0}  # placeholder

# Async runner for both FastAPI + Telegram
async def run_all():
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling()
    await telegram_app.updater.idle()

# Start everything together if launched directly
if __name__ == "__main__":
    try:
        asyncio.run(run_all())
    except (KeyboardInterrupt, SystemExit):
        logging.info("ZariahBot stopped manually.")


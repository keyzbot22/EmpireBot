import asyncio
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "7329634509:AAG2sydFNeF02HuNYV8L9fDDXZViecXa7uA"
WEBHOOK_SECRET = "zariah-webhook"
WEBHOOK_PATH = f"/webhook/{WEBHOOK_SECRET}"
BOT_URL = f"https://skillful-energy.up.railway.app{WEBHOOK_PATH}"

app = FastAPI()
telegram_app = Application.builder().token(TOKEN).build()

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    json_data = await request.json()
    update = Update.de_json(json_data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "ZariahBot webhook is alive!"}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Webhook is working!")

telegram_app.add_handler(CommandHandler("start", start_command))

@app.on_event("startup")
async def startup():
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(url=BOT_URL)

import uvicorn

if __name__ == "__main__":
    uvicorn.run("webhook_bot:app", host="0.0.0.0", port=8000)


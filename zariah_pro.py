import os
import logging
import asyncio
import requests
from datetime import datetime
from telegram import Update, constants
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from metaapi_cloud_sdk import MetaApi
from fastapi import FastAPI
import uvicorn

class Config:
    BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
    METAAPI_TOKEN = os.getenv("METAAPI_TOKEN")
    MT4_ACCOUNT_ID = os.getenv("MT4_ACCOUNT_ID")
    DEEPSEEK_URL = os.getenv("DEEPSEEK_URL", "http://deepseek:8000/scan")
    DEPLOY_MODE = os.getenv("DEPLOY_MODE", "polling").lower()
    PORT = int(os.getenv("PORT", 8000))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ZariahBot")

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "online", "timestamp": datetime.utcnow().isoformat()}

class TradingBot:
    def __init__(self):
        self.metaapi = MetaApi(Config.METAAPI_TOKEN)
        self.account = None

    async def connect_mt4(self):
        for attempt in range(3):
            try:
                self.account = await self.metaapi.metatrader_account_api.get_account(Config.MT4_ACCOUNT_ID)
                await self.account.deploy()
                await self.account.wait_connected(timeout=30)
                return await self.account.get_rpc_connection()
            except Exception as e:
                logger.error(f"MT4 connection attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(5)

    async def execute_trade(self, symbol: str, action: str, volume: float = 0.01):
        try:
            connection = await self.connect_mt4()
            result = await connection.create_market_order(symbol=symbol, action=action.lower(), volume=volume)
            return result
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            return None

async def deepseek_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        symbol = context.args[0].upper() if context.args else "BTC"
        logger.info(f"Scanning symbol: {symbol}")
        response = requests.post(Config.DEEPSEEK_URL, json={"symbol": symbol}, timeout=10)
        response.raise_for_status()
        data = response.json()
        message = (
            f"*📊 {symbol} Analysis*
"
            f"• Action: {data['action']}
"
            f"• Confidence: {data['confidence']:.2f}
"
            f"• Time: {data['timestamp']}
"
            f"────────────
"
            f"`/trade {data['action'].lower()} {symbol} 0.01`"
        )
        await update.message.reply_text(message, parse_mode=constants.ParseMode.MARKDOWN_V2)
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        await update.message.reply_text("⚠️ Scan service unavailable")

async def start_bot():
    bot = TradingBot()
    app_builder = ApplicationBuilder().token(Config.BOT_TOKEN).build()
    app_builder.add_handler(CommandHandler("deepseek", deepseek_scan))
    if Config.DEPLOY_MODE == "webhook":
        await app_builder.bot.set_webhook(f"{os.getenv('WEBHOOK_URL')}/telegram")
    else:
        await app_builder.run_polling()

if __name__ == "__main__":
    config = uvicorn.Config(app, host="0.0.0.0", port=Config.PORT, log_level="info")
    server = uvicorn.Server(config)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(asyncio.gather(server.serve(), start_bot()))
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
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
import re

# Configuration class for env variables
class Config:
    BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
    METAAPI_TOKEN = os.getenv("METAAPI_TOKEN")
    MT4_ACCOUNT_ID = os.getenv("MT4_ACCOUNT_ID")
    DEEPSEEK_URL = os.getenv("DEEPSEEK_URL", "http://deepseek:8000/scan")
    DEPLOY_MODE = os.getenv("DEPLOY_MODE", "polling").lower()
    PORT = int(os.getenv("PORT", 8000))

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ZariahBot")

# FastAPI app for health check
app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "online", "timestamp": datetime.utcnow().isoformat()}

# MetaTrader TradingBot class
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

# Markdown escaping for Telegram formatting
def escape_md(text):
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

# /deepseek command handler
async def deepseek_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = context.args[0].upper() if context.args else "BTC"
    for attempt in range(3):
        try:
            logger.info(f"Scanning {symbol} attempt {attempt + 1}")
            response = requests.post(Config.DEEPSEEK_URL, json={"symbol": symbol}, timeout=10)
            response.raise_for_status()
            data = response.json()

            action = escape_md(data['action'])
            symbol_escaped = escape_md(symbol)

            message = (
                f"*📊 {symbol_escaped} Analysis*\n"
                f"• Action: {action}\n"
                f"• Confidence: {data['confidence']:.2f}\n"
                f"• Time: {escape_md(data['timestamp'])}\n"
                f"────────────\n"
                f"`/trade {data['action'].lower()} {symbol} 0.01`"
            )
            await update.message.reply_text(message, parse_mode=constants.ParseMode.MARKDOWN_V2)
            return
        except Exception as e:
            logger.warning(f"DeepSeek scan attempt {attempt + 1} failed: {e}")
            await asyncio.sleep(2)
    await update.message.reply_text("⚠️ DeepSeek scan failed after 3 attempts.")

# /trade command handler
async def trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        action, symbol, volume = context.args[0], context.args[1], float(context.args[2])
        bot = TradingBot()
        result


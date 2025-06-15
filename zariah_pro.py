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
from typing import Optional

# Configuration class with type hints
class Config:
    BOT_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
    METAAPI_TOKEN: str = os.getenv("METAAPI_TOKEN", "")
    MT4_ACCOUNT_ID: str = os.getenv("MT4_ACCOUNT_ID", "")
    DEEPSEEK_URL: str = os.getenv("DEEPSEEK_URL", "http://deepseek:8000/scan")
    DEPLOY_MODE: str = os.getenv("DEPLOY_MODE", "polling").lower()
    PORT: int = int(os.getenv("PORT", "8000"))

# Enhanced logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger("ZariahBot")

# FastAPI app
app = FastAPI(
    title="Zariah Trading Bot API",
    description="Provides health checks and monitoring for the trading bot"
)

@app.get("/health")
async def health():
    return {
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "metaapi": Config.METAAPI_TOKEN != "",
            "telegram": Config.BOT_TOKEN != ""
        }
    }

class TradingBot:
    def __init__(self):
        self.metaapi = MetaApi(Config.METAAPI_TOKEN)
        self.account = None
        self.connection_pool = {}

    async def get_connection(self) -> Optional[object]:
        if not self.account:
            await self.connect_mt4()
        return await self.account.get_rpc_connection()

    async def connect_mt4(self, retries: int = 3) -> bool:
        for attempt in range(retries):
            try:
                self.account = await self.metaapi.metatrader_account_api.get_account(Config.MT4_ACCOUNT_ID)
                await self.account.deploy()
                await self.account.wait_connected(timeout=30)
                logger.info("Successfully connected to MT4 account")
                return True
            except Exception as e:
                wait_time = min(2 ** attempt, 10)
                logger.error(f"MT4 connection attempt {attempt + 1} failed. Retrying in {wait_time}s... Error: {e}")
                await asyncio.sleep(wait_time)
        logger.error("Failed to connect to MT4 after maximum retries")
        return False

    async def execute_trade(self, symbol: str, action: str, volume: float = 0.01) -> Optional[dict]:
        try:
            connection = await self.get_connection()
            if not connection:
                return None

            result = await connection.create_market_order(
                symbol=symbol,
                action=action.lower(),
                volume=volume
            )
            logger.info(f"Trade executed: {symbol} {action} {volume}")
            return result
        except Exception as e:
            logger.error(f"Trade execution error: {e}")
            return None

def escape_md(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'([_\*\[\]()~`>#+\-=|{}.!])', r'\\\1', str(text))

async def deepseek_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = context.args[0].upper() if context.args else "BTC"

    for attempt in range(3):
        try:
            logger.info(f"DeepSeek scan attempt {attempt + 1} for {symbol}")

            response = requests.post(
                Config.DEEPSEEK_URL,
                json={"symbol": symbol},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            message = (
                f"*\ud83d\udcca {escape_md(symbol)} Analysis*\n"
                f"\u2022 *Action*: {escape_md(data.get('action', 'N/A'))}\n"
                f"\u2022 *Confidence*: {data.get('confidence', 0):.2f}\n"
                f"\u2022 *Time*: {escape_md(data.get('timestamp', 'N/A'))}\n"
                f"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
                f"`/trade {data['action'].lower()} {symbol} 0.01`"
            )

            await update.message.reply_text(
                message,
                parse_mode=constants.ParseMode.MARKDOWN_V2
            )
            return

        except Exception as e:
            logger.warning(f"Scan attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                await asyncio.sleep(2)

    await update.message.reply_text(
        "\u26a0\ufe0f Scan service unavailable after multiple attempts",
        parse_mode=constants.ParseMode.MARKDOWN_V2
    )

async def trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage: /trade <buy/sell> <symbol> <volume>",
            parse_mode=constants.ParseMode.MARKDOWN_V2
        )
        return

    try:
        action, symbol, volume = context.args[0], context.args[1].upper(), float(context.args[2])

        if action.lower() not in ['buy', 'sell']:
            raise ValueError("Action must be 'buy' or 'sell'")

        bot = TradingBot()
        result = await bot.execute_trade(symbol, action, volume)

        if result:
            await update.message.reply_text(
                f"\u2705 Trade executed:\n"
                f"*{escape_md(symbol)} {escape_md(action.upper())} {escape_md(volume)}*",
                parse_mode=constants.ParseMode.MARKDOWN_V2
            )
        else:
            await update.message.reply_text(
                "\u26a0\ufe0f Failed to execute trade",
                parse_mode=constants.ParseMode.MARKDOWN_V2
            )

    except ValueError as e:
        await update.message.reply_text(
            f"\u274c Invalid input: {escape_md(str(e))}",
            parse_mode=constants.ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Trade command error: {e}")
        await update.message.reply_text(
            "\u26a0\ufe0f An error occurred while processing your trade",
            parse_mode=constants.ParseMode.MARKDOWN_V2
        )

async def start_bot():
    app_builder = ApplicationBuilder().token(Config.BOT_TOKEN)
    app = app_builder.build()
    app.add_handler(CommandHandler("deepseek", deepseek_scan))
    app.add_handler(CommandHandler("trade", trade_command))

    if Config.DEPLOY_MODE == "webhook":
        await app.bot.set_webhook(f"{os.getenv('WEBHOOK_URL')}/telegram")
        logger.info("Webhook mode activated")
    else:
        logger.info("Starting in polling mode")
        await app.run_polling()

async def run_services():
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=Config.PORT,
        log_level="info",
        loop="asyncio"
    )
    server = uvicorn.Server(config)

    await asyncio.gather(
        server.serve(),
        start_bot()
    )

if __name__ == "__main__":
    if not all([Config.BOT_TOKEN, Config.METAAPI_TOKEN, Config.MT4_ACCOUNT_ID]):
        logger.error("Missing required environment variables")
        exit(1)

    try:
        asyncio.run(run_services())
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        logger.info("Bot service stopped")

import os
import logging
import requests
import telegram
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from metaapi_cloud_sdk import MetaApi
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

BOT_TOKEN = os.getenv("ZARIAH_BOT_TOKEN")
DEEPSEEK_URL = "http://localhost:8055/scan"
METAAPI_TOKEN = os.getenv("METAAPI_TOKEN")
MT4_ACCOUNT_ID = "85214d00-75f0-4191-8c02-66c9ef37d066"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Zariah")

metaapi = MetaApi(METAAPI_TOKEN)

def escape_markdown(text):
    escape_chars = r"\\_*[]()~`>#+-=|{}.!"
    return ''.join(f"\\{c}" if c in escape_chars else c for c in str(text))

async def deepseek_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        symbol = context.args[0].upper() if context.args else "BTC"
        logger.info(f"[ZARIAH DEBUG] Scanning: {symbol}")

        response = requests.post(DEEPSEEK_URL, json={"symbol": symbol}, timeout=10)
        response.raise_for_status()
        data = response.json()

        confidence = data.get("confidence", 0)
        action = data.get("action", "HOLD")

        result = (
            f"*📊 DeepSeek Scan*
"
            f"• Symbol: `{escape_markdown(data['symbol'])}`\n"
            f"• Action: *{escape_markdown(action)}*\n"
            f"• Confidence: `{confidence}`\n"
            f"• Time: `{escape_markdown(data['timestamp'])}`\n"
            f"────────────\n"
            f"`/trade hugosway {escape_markdown(action.lower())} {escape_markdown(data['symbol'])} 0.01`"
        )

        await update.message.reply_text(result, parse_mode=telegram.constants.ParseMode.MARKDOWN_V2)
        logger.info("[ZARIAH DEBUG] Scan sent")

        if confidence >= 0.9:
            await context.bot.send_message(
                chat_id="@your_group",
                text=f"🚨 STRONG SIGNAL: {action} {symbol} (Confidence: {confidence*100:.1f}%)"
            )

    except Exception as e:
        logger.error(f"[ZARIAH ERROR] {e}")
        await update.message.reply_text("🔴 DeepSeek system error. Check logs.")

async def execute_mt4_trade(symbol, action, volume=0.01):
    try:
        account = await metaapi.metatrader_account_api.get_account(MT4_ACCOUNT_ID)
        await account.deploy()
        await account.wait_connected()
        connection = await account.get_rpc_connection()
        await connection.connect()

        trade = await connection.create_market_order(
            symbol=symbol,
            action=action.lower(),
            volume=volume
        )
        logger.info(f"✅ MT4 trade executed: {trade}")
        return trade
    except Exception as e:
        logger.error(f"❌ MT4 trade failed: {e}")
        return None

def auto_scan():
    logger.info("🔄 Auto-scan triggered")
    try:
        requests.post(DEEPSEEK_URL, json={"symbol": "BTC"})
    except Exception as e:
        logger.error(f"Auto-scan failed: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(auto_scan, 'interval', minutes=15)
scheduler.start()

def main():
    logger.info("🚀 ZariahBot is live")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("deepseek", deepseek_scan))
    app.run_polling()

if __name__ == "__main__":
    main()


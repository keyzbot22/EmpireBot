import os, logging, requests, telegram
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = "7329634509:AAG2sydFNeF02HuNYV8L9fDDXZViecXa7uA"
DEEPSEEK_URL = "http://localhost:8055/scan"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def escape_markdown(text):
    escape_chars = r"\_*[]()~`>#+-=|{}.!"
    return ''.join(f"\\{c}" if c in escape_chars else c for c in str(text))

async def deepseek_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        symbol = context.args[0].upper() if context.args else "BTC"
        logger.info(f"[ZARIAH DEBUG] Scanning: {symbol}")
        response = requests.post(DEEPSEEK_URL, json={"symbol": symbol}, timeout=10)
        response.raise_for_status()
        data = response.json()

        result = (
            f"*📊 DeepSeek Scan*\n"
            f"• Symbol: `{escape_markdown(data['symbol'])}`\n"
            f"• Action: *{escape_markdown(data['action'])}*\n"
            f"• Confidence: `{data['confidence']}`\n"
            f"• Time: `{escape_markdown(data['timestamp'])}`\n"
            f"────────────\n"
            f"`/trade coinbase {escape_markdown(data['action'].lower())} {escape_markdown(data['symbol'])} 0.01`"
        )

        await update.message.reply_text(result, parse_mode=telegram.constants.ParseMode.MARKDOWN_V2)
        logger.info("[ZARIAH DEBUG] Scan sent")

    except Exception as e:
        logger.error(f"[ZARIAH ERROR] {e}")
        await update.message.reply_text("🔴 DeepSeek system error. Check logs.")

def main():
    logger.info("🚀 ZariahBot online and listening...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("deepseek", deepseek_scan))
    app.run_polling()

if __name__ == "__main__":
    main()


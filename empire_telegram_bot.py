
# empire_telegram_bot.py
# Requires python-telegram-bot: pip install python-telegram-bot

from telegram.ext import Updater, CommandHandler
import requests

BOT_TOKEN = "YOUR_BOTFATHER_TOKEN"
AUTHORIZED_ID = 123456789  # Replace with your Telegram ID

def handle_command(update, context):
    user_id = update.effective_user.id
    if user_id != AUTHORIZED_ID:
        update.message.reply_text("❌ Unauthorized.")
        return

    command = update.message.text.strip("/")
    response = requests.post("http://127.0.0.1:5005/bot-command", json={"user": "kingkash223", "command": command})
    update.message.reply_text(response.json().get("result", "Unknown response."))

updater = Updater(BOT_TOKEN)
updater.dispatcher.add_handler(CommandHandler(["start_trading", "log_income", "post_content", "backup"], handle_command))

print("✅ Telegram Bot Running")
updater.start_polling()
updater.idle()

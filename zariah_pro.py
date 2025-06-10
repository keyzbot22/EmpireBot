kimport asyncio
import nest_asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Allow nested event loops (required for Mac OS or Jupyter/IDE environments)
nest_asyncio.apply()

# === Command Handlers ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    await update.message.reply_text("🤖 ZariahBot Activated!")

async def profit_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Today's profits are being calculated...")

async def trade_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📈 Trade report generated.")

async def blast_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚨 ALERT: Trigger sent to all systems.")

async def restart_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔁 Restarting all modules...")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ System Status: Online\n📡 Bots Linked: Zariah, DeepSeek, EmpireBot, Trading Modules")

async def stress_test(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    await update.message.reply_text("🔧 Stress test initiated. Running diagnostics...")

# === Main Application ===

async def run_bot():
    app = Application.builder().token("7329634509:AAG2sydFNeF02HuNYV8L9fDDXZViecXa7uA").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profit_today", profit_today))
    app.add_handler(CommandHandler("trade_report", trade_report))
    app.add_handler(CommandHandler("blast", blast_alert))
    app.add_handler(CommandHandler("restart_all", restart_all))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("stress_test", stress_test))

    print("🚀 ZariahBot is now running in polling mode...")
    await app.run_polling()

# Entry point
loop = asyncio.get_event_loop()
loop.run_until_complete(run_bot())


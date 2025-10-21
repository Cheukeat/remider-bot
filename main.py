import os
import asyncio
from datetime import datetime, timedelta
import parsedatetime as pdt
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv

# Load BOT_TOKEN from .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Store reminders in memory (for demo; for persistent storage use a database)
reminders = []

# Parse natural language time strings
calendar = pdt.Calendar()

# ---------------- Handlers ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Smart Reminder Bot is running!\nForward me a message with a time like 'in 30 minutes' or 'at 7:30 PM' and I'll remind you.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    user_id = update.message.from_user.id

    # Try to parse time from message
    time_struct, parse_status = calendar.parse(msg)
    if parse_status == 0:
        await update.message.reply_text("❌ Could not understand the time. Try 'in 30 minutes' or 'at 7:30 PM'.")
        return

    reminder_time = datetime(*time_struct[:6])
    if reminder_time < datetime.now():
        await update.message.reply_text("❌ That time is in the past!")
        return

    # Save reminder
    reminders.append({
        "user_id": user_id,
        "text": msg,
        "time": reminder_time
    })
    await update.message.reply_text(f"✅ Reminder set for {reminder_time.strftime('%Y-%m-%d %H:%M:%S')}")

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_reminders = [r for r in reminders if r["user_id"] == user_id]
    if not user_reminders:
        await update.message.reply_text("You have no reminders.")
        return

    text = "📋 Your reminders:\n"
    for i, r in enumerate(user_reminders, 1):
        text += f"{i}. {r['text']} at {r['time'].strftime('%Y-%m-%d %H:%M:%S')}\n"
    await update.message.reply_text(text)

async def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /delete <reminder number>")
        return

    try:
        index = int(args[0]) - 1
    except ValueError:
        await update.message.reply_text("❌ Invalid number")
        return

    user_reminders = [r for r in reminders if r["user_id"] == user_id]
    if index < 0 or index >= len(user_reminders):
        await update.message.reply_text("❌ Reminder number out of range")
        return

    reminder_to_delete = user_reminders[index]
    reminders.remove(reminder_to_delete)
    await update.message.reply_text("✅ Reminder deleted.")

# ---------------- Reminder Loop ----------------
async def reminder_loop(app):
    while True:
        now = datetime.now()
        for r in reminders[:]:
            if r["time"] <= now:
                try:
                    await app.bot.send_message(chat_id=r["user_id"], text=f"⏰ Reminder: {r['text']}")
                except Exception as e:
                    print(f"Failed to send reminder: {e}")
                reminders.remove(r)
        await asyncio.sleep(30)  # check every 30 seconds

# ---------------- Main ----------------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_reminders))
    app.add_handler(CommandHandler("delete", delete_reminder))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start reminder loop
    app.create_task(reminder_loop(app))

    # Run the bot
    await app.run_polling()

# Run main
if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())

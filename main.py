import nest_asyncio
nest_asyncio.apply()

import asyncio
import json, os
from datetime import datetime, timedelta

import pytz
import parsedatetime as pdt
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# Load .env
load_dotenv()
BOT_TOKEN = os.environ["BOT_TOKEN"]
TIMEZONE = pytz.timezone(os.environ.get("TIMEZONE", "Asia/Phnom_Penh"))
REMINDER_FILE = "reminders.json"

# Load/save reminders
def load_reminders():
    if os.path.exists(REMINDER_FILE):
        with open(REMINDER_FILE, "r") as f:
            return json.load(f)
    return {}

def save_reminders(data):
    with open(REMINDER_FILE, "w") as f:
        json.dump(data, f, indent=2)

reminders = load_reminders()
cal = pdt.Calendar()

# /start command
async def start(update, context):
    await update.message.reply_text(
        "👋 Smart Reminder Bot running!\n\n"
        "Commands:\n"
        "/list - show all reminders\n"
        "/delete <id> - delete a reminder\n"
        "Send a message or forward a picture/file with 'Remind me in 30 minutes' or 'Remind me at 8pm'"
    )

# Parse natural language time
def parse_time(text):
    time_struct, status = cal.parse(text)
    if status == 0:
        return None
    dt = datetime(*time_struct[:6])
    if dt < datetime.now():
        dt += timedelta(days=1)
    return TIMEZONE.localize(dt)

# Handle message to create reminder
async def handle_message(update, context):
    user_id = str(update.effective_user.id)
    text = update.message.text or ""

    # Check for media
    media = None
    if update.message.photo:
        media = {"type": "photo", "file_id": update.message.photo[-1].file_id}
    elif update.message.document:
        media = {"type": "document", "file_id": update.message.document.file_id}

    # Parse time
    t = parse_time(text)
    if not t:
        await update.message.reply_text("⚠️ Could not parse time from your message.")
        return

    reminders.setdefault(user_id, []).append({
        "text": text,
        "time": t.isoformat(),
        "media": media
    })
    save_reminders(reminders)
    await update.message.reply_text(f"✅ Reminder set for {t.strftime('%Y-%m-%d %I:%M %p')}")

# /list command
async def list_reminders(update, context):
    user_id = str(update.effective_user.id)
    user_reminders = reminders.get(user_id, [])
    if not user_reminders:
        await update.message.reply_text("📭 No reminders set.")
        return
    msg = "🗓 Your Reminders:\n"
    for i, r in enumerate(user_reminders, start=1):
        t = datetime.fromisoformat(r["time"]).strftime("%Y-%m-%d %I:%M %p")
        msg += f"{i}. {t} — {r['text']}\n"
    await update.message.reply_text(msg)

# /delete command
async def delete_reminder(update, context):
    user_id = str(update.effective_user.id)
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /delete <id>")
        return
    idx = int(args[0]) - 1
    if user_id in reminders and 0 <= idx < len(reminders[user_id]):
        removed = reminders[user_id].pop(idx)
        save_reminders(reminders)
        await update.message.reply_text(f"🗑 Deleted reminder: {removed['text']}")
    else:
        await update.message.reply_text("⚠️ Invalid reminder ID.")

# Reminder loop
async def reminder_loop(app):
    while True:
        now = datetime.now(TIMEZONE)
        changed = False
        for user_id, items in list(reminders.items()):
            for item in list(items):
                t = datetime.fromisoformat(item["time"])
                if t <= now:
                    try:
                        if item.get("media"):
                            if item["media"]["type"] == "photo":
                                await app.bot.send_photo(chat_id=int(user_id),
                                                         photo=item["media"]["file_id"],
                                                         caption=f"🔔 Reminder:\n{item['text']}")
                            elif item["media"]["type"] == "document":
                                await app.bot.send_document(chat_id=int(user_id),
                                                            document=item["media"]["file_id"],
                                                            caption=f"🔔 Reminder:\n{item['text']}")
                        else:
                            await app.bot.send_message(chat_id=int(user_id),
                                                       text=f"🔔 Reminder:\n{item['text']}")
                    except:
                        pass
                    items.remove(item)
                    changed = True
        if changed:
            save_reminders(reminders)
        await asyncio.sleep(30)

# Main app
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_reminders))
    app.add_handler(CommandHandler("delete", delete_reminder))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    app.create_task(reminder_loop(app))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())

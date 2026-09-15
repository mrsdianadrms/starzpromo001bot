import os
import sqlite3
import logging
from datetime import datetime, time as dtime

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

from content import ANNIVERSARY_EVENTS, WEEKLY_MESSAGE

# ---------- Configuration ----------
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
DB_PATH = "starzpromo.db"

# Time of day the bot checks and sends updates (UTC). Default 09:00 UTC.
SEND_HOUR_UTC = int(os.environ.get("SEND_HOUR_UTC", "9"))
SEND_MINUTE_UTC = int(os.environ.get("SEND_MINUTE_UTC", "0"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------- Database ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            subscribed_at TEXT,
            last_sent_date TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sent_log (
            event_key TEXT,
            sent_date TEXT,
            recipients INTEGER,
            PRIMARY KEY (event_key, sent_date)
        )
    """)
    conn.commit()
    conn.close()

def db_execute(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    result = c.fetchall()
    conn.close()
    return result

def add_subscriber(user):
    db_execute(
        "INSERT OR IGNORE INTO subscribers (user_id, username, first_name, subscribed_at) VALUES (?,?,?,?)",
        (user.id, user.username or "", user.first_name or "", datetime.utcnow().isoformat())
    )

def get_all_subscribers():
    return db_execute("SELECT user_id FROM subscribers")

def already_sent_today(event_key, today):
    rows = db_execute(
        "SELECT 1 FROM sent_log WHERE event_key=? AND sent_date=?",
        (event_key, today)
    )
    return bool(rows)

def log_send(event_key, today, recipients):
    db_execute(
        "INSERT OR REPLACE INTO sent_log (event_key, sent_date, recipients) VALUES (?,?,?)",
        (event_key, today, recipients)
    )

# ---------- Automatic Daily Sender ----------
async def daily_check(context: ContextTypes.DEFAULT_TYPE):
    """Runs once per day. Sends the matching anniversary message if any."""
    now = datetime.utcnow()
    today_key = now.strftime("%m-%d")   # MM-DD
    today_full = now.strftime("%Y-%m-%d")

    event = ANNIVERSARY_EVENTS.get(today_key)

    # Fallback: weekly message on Mondays if no daily event
    if not event and WEEKLY_MESSAGE and now.weekday() == 0:
        event = WEEKLY_MESSAGE
        event_key = "weekly"
    elif event:
        event_key = today_key
    else:
        logger.info("No event today (%s). Nothing sent.", today_full)
        return

    if already_sent_today(event_key, today_full):
        logger.info("Event %s already sent today. Skipping.", event_key)
        return

    subscribers = get_all_subscribers()
    delivered = 0
    text = f"🎉 <b>{event['title']}</b>\n\n{event['message']}"

    for (uid,) in subscribers:
        try:
            await context.bot.send_message(chat_id=uid, text=text, parse_mode="HTML")
            delivered += 1
        except Exception as e:
            logger.warning("Failed to send to %s: %s", uid, e)

    log_send(event_key, today_full, delivered)
    logger.info("Sent event '%s' to %d subscriber(s).", event_key, delivered)

# ---------- /start ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_subscriber(user)

    keyboard = [
        [InlineKeyboardButton("📅 Today's Update", callback_data="today_update")],
        [InlineKeyboardButton("📖 Full Anniversary List", callback_data="list_events")],
        [InlineKeyboardButton("🔔 Subscription Status", callback_data="sub_status")],
        [InlineKeyboardButton("ℹ️ About", callback_data="about_bot")],
    ]

    await update.message.reply_text(
        f"👋 Welcome to <b>Starz Promo</b>, {user.first_name}!\n\n"
        "You are now subscribed to automatic anniversary event updates.\n\n"
        "The bot will send you the right update on the right day — no need to do anything.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ---------- Today's Update ----------
async def today_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    now = datetime.utcnow()
    today_key = now.strftime("%m-%d")
    event = ANNIVERSARY_EVENTS.get(today_key)

    if not event:
        text = "📅 <b>No anniversary event today.</b>\n\nCheck back tomorrow — updates arrive automatically."
    else:
        text = f"🎉 <b>{event['title']}</b>\n\n{event['message']}"

    await query.edit_message_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_start")]])
    )

# ---------- Full Anniversary List ----------
async def list_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not ANNIVERSARY_EVENTS:
        text = "No events configured yet."
    else:
        text = "📖 <b>Anniversary Events Calendar</b>\n\n"
        for date_key in sorted(ANNIVERSARY_EVENTS.keys()):
            ev = ANNIVERSARY_EVENTS[date_key]
            text += f"• <b>{date_key}</b> — {ev['title']}\n"

    await query.edit_message_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_start")]])
    )

# ---------- Subscription Status ----------
async def sub_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    exists = db_execute("SELECT 1 FROM subscribers WHERE user_id=?", (user.id,))
    total = db_execute("SELECT COUNT(*) FROM subscribers")[0][0]

    status_text = "✅ You are <b>subscribed</b> to automatic updates." if exists else \
                  "❌ You are <b>not subscribed</b>. Send /start to subscribe."

    await query.edit_message_text(
        f"🔔 <b>Subscription Status</b>\n\n{status_text}\n\n👥 Total subscribers: {total}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_start")]])
    )

# ---------- About ----------
async def about_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "ℹ️ <b>About Starz Promo</b>\n\n"
        "Starz Promo automatically delivers anniversary event updates, schedules, and announcements "
        "to your Telegram on the right day.\n\n"
        "Simply subscribe once with /start and receive updates as they happen. "
        "No spam, no external links.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_start")]])
    )

# ---------- Back ----------
async def back_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    keyboard = [
        [InlineKeyboardButton("📅 Today's Update", callback_data="today_update")],
        [InlineKeyboardButton("📖 Full Anniversary List", callback_data="list_events")],
        [InlineKeyboardButton("🔔 Subscription Status", callback_data="sub_status")],
        [InlineKeyboardButton("ℹ️ About", callback_data="about_bot")],
    ]

    await query.edit_message_text(
        f"👋 Welcome back, {user.first_name}!\n\nChoose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- Post-init: schedule daily job ----------
async def on_startup(app: Application):
    # Schedule the daily check
    t = dtime(hour=SEND_HOUR_UTC, minute=SEND_MINUTE_UTC)
    app.job_queue.run_daily(daily_check, time=t)
    logger.info("Daily anniversary check scheduled at %02d:%02d UTC.", SEND_HOUR_UTC, SEND_MINUTE_UTC)

# ---------- Main ----------
def main():
    if not BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN environment variable is required.")

    init_db()

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(on_startup)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(today_update, pattern="^today_update$"))
    app.add_handler(CallbackQueryHandler(list_events, pattern="^list_events$"))
    app.add_handler(CallbackQueryHandler(sub_status, pattern="^sub_status$"))
    app.add_handler(CallbackQueryHandler(about_bot, pattern="^about_bot$"))
    app.add_handler(CallbackQueryHandler(back_start, pattern="^back_start$"))

    logger.info("Starz Promo bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()

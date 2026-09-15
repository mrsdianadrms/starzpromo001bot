import os
import sqlite3
import logging
from datetime import datetime

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ---------- Configuration ----------
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
DB_PATH = "starzpromo.db"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states for posting an event
(EVENT_TITLE, EVENT_DATE, EVENT_DETAILS) = range(3)

# ---------- Database ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            subscribed_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            event_date TEXT,
            details TEXT,
            created_at TEXT
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

# ---------- /start ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_subscriber(user)

    keyboard = [
        [InlineKeyboardButton("📅 Upcoming Events", callback_data="view_events")],
        [InlineKeyboardButton("🔔 Subscription Status", callback_data="sub_status")],
        [InlineKeyboardButton("ℹ️ About", callback_data="about_bot")],
    ]
    if user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("➕ Post New Event", callback_data="post_event")])

    await update.message.reply_text(
        f"👋 Welcome to <b>Starz Promo</b>, {user.first_name}!\n\n"
        "You are now subscribed to official anniversary event updates.\n\n"
        "You'll receive:\n"
        "• Event schedules\n"
        "• Announcements\n"
        "• Reminders\n\n"
        "Use the buttons below to explore.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# ---------- View Events ----------
async def view_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    rows = db_execute(
        "SELECT id, title, event_date, details FROM events ORDER BY id DESC LIMIT 10"
    )
    if not rows:
        await query.edit_message_text(
            "📅 <b>No events posted yet.</b>\n\nCheck back soon for anniversary updates!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_start")]])
        )
        return

    text = "📅 <b>Upcoming Events</b>\n\n"
    for eid, title, edate, details in rows:
        text += f"🎉 <b>{title}</b>\n📆 {edate}\n{details}\n\n"

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

    if exists:
        status_text = "✅ You are <b>subscribed</b> to event updates."
    else:
        status_text = "❌ You are <b>not subscribed</b>. Send /start to subscribe."

    await query.edit_message_text(
        f"🔔 <b>Subscription Status</b>\n\n{status_text}\n\n"
        f"👥 Total subscribers: {total}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_start")]])
    )

# ---------- About ----------
async def about_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "ℹ️ <b>About Starz Promo</b>\n\n"
        "Starz Promo delivers official anniversary event updates directly to your Telegram.\n\n"
        "Start the bot to receive schedules, announcements, reminders, and event info as they happen.\n\n"
        "No spam. No external links. Just timely updates you can trust.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_start")]])
    )

# ---------- Back to Start ----------
async def back_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    keyboard = [
        [InlineKeyboardButton("📅 Upcoming Events", callback_data="view_events")],
        [InlineKeyboardButton("🔔 Subscription Status", callback_data="sub_status")],
        [InlineKeyboardButton("ℹ️ About", callback_data="about_bot")],
    ]
    if user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("➕ Post New Event", callback_data="post_event")])

    await query.edit_message_text(
        f"👋 Welcome back, {user.first_name}!\n\nChoose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- Admin: Post Event (Conversation) ----------
async def post_event_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id != ADMIN_ID:
        await query.answer("Only the admin can post events.", show_alert=True)
        return ConversationHandler.END
    await query.edit_message_text("📝 Enter the <b>event title</b>:", parse_mode="HTML")
    return EVENT_TITLE

async def post_event_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ev_title"] = update.message.text
    await update.message.reply_text("📆 Enter the <b>event date</b> (e.g., 2025-12-25 or 'Dec 25, 2025'):")
    return EVENT_DATE

async def post_event_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ev_date"] = update.message.text
    await update.message.reply_text("📄 Enter the <b>event details</b> (short description):")
    return EVENT_DETAILS

async def post_event_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    details = update.message.text
    title = context.user_data["ev_title"]
    edate = context.user_data["ev_date"]

    db_execute(
        "INSERT INTO events (title, event_date, details, created_at) VALUES (?,?,?,?)",
        (title, edate, details, datetime.utcnow().isoformat())
    )

    # Broadcast to all subscribers
    subscribers = get_all_subscribers()
    delivered = 0
    for (uid,) in subscribers:
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"🎉 <b>New Event Update!</b>\n\n"
                     f"<b>{title}</b>\n"
                     f"📆 {edate}\n\n"
                     f"{details}",
                parse_mode="HTML"
            )
            delivered += 1
        except Exception:
            pass

    await update.message.reply_text(
        f"✅ <b>Event posted!</b>\n\n"
        f"📌 {title}\n"
        f"📆 {edate}\n"
        f"📄 {details}\n\n"
        f"📤 Broadcast delivered to {delivered} subscriber(s).",
        parse_mode="HTML"
    )
    return ConversationHandler.END

async def cancel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Event posting cancelled.")
    return ConversationHandler.END

# ---------- Admin: Broadcast a custom message ----------
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Only the admin can broadcast.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast Your message here")
        return

    message = " ".join(context.args)
    subscribers = get_all_subscribers()
    delivered = 0
    for (uid,) in subscribers:
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"📢 <b>Announcement</b>\n\n{message}",
                parse_mode="HTML"
            )
            delivered += 1
        except Exception:
            pass

    await update.message.reply_text(f"📤 Broadcast sent to {delivered} subscriber(s).")

# ---------- Admin: Subscriber count ----------
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Only the admin can view stats.")
        return
    total = db_execute("SELECT COUNT(*) FROM subscribers")[0][0]
    events = db_execute("SELECT COUNT(*) FROM events")[0][0]
    await update.message.reply_text(
        f"📊 <b>Bot Stats</b>\n\n"
        f"👥 Subscribers: {total}\n"
        f"📅 Events posted: {events}",
        parse_mode="HTML"
    )

# ---------- Main ----------
def main():
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set.")
        raise SystemExit("TELEGRAM_BOT_TOKEN environment variable is required.")

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats", stats))

    # Conversation for posting events
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(post_event_start, pattern="^post_event$")],
        states={
            EVENT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_event_title)],
            EVENT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_event_date)],
            EVENT_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_event_details)],
        },
        fallbacks=[CommandHandler("cancel", cancel_post)],
    )
    app.add_handler(conv_handler)

    # Callbacks
    app.add_handler(CallbackQueryHandler(view_events, pattern="^view_events$"))
    app.add_handler(CallbackQueryHandler(sub_status, pattern="^sub_status$"))
    app.add_handler(CallbackQueryHandler(about_bot, pattern="^about_bot$"))
    app.add_handler(CallbackQueryHandler(back_start, pattern="^back_start$"))

    logger.info("Starz Promo bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()

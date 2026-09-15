# Starz Promo Bot

A Telegram bot that automatically sends anniversary event updates to subscribers — no manual work needed.

## How It Works
- All anniversary messages are stored in `content.py`
- The bot checks the date every day at 09:00 UTC
- If today matches an event, it broadcasts automatically to all subscribers
- If today is Monday and no event is set, a weekly message is sent

## Setup
1. Edit `content.py` and add your anniversary events using "MM-DD" keys.
2. Push to GitHub.
3. Deploy on Railway with `TELEGRAM_BOT_TOKEN` set.

## Environment Variables
- `TELEGRAM_BOT_TOKEN` — from BotFather
- `SEND_HOUR_UTC` — optional, default `9`
- `SEND_MINUTE_UTC` — optional, default `0`

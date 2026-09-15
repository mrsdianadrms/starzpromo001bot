# Starz Promo Bot

A Telegram bot that delivers official anniversary event updates, schedules, and announcements to subscribers.

## Features
- Users subscribe automatically on /start
- Admin can post events with title, date, and details
- Broadcasts event updates to all subscribers
- View upcoming events from the menu
- Check subscription status

## Environment Variables (Railway)
- `TELEGRAM_BOT_TOKEN` — from BotFather
- `ADMIN_ID` — your Telegram user ID

## Commands
- `/start` — subscribe and open main menu
- `/broadcast <message>` — send a message to all subscribers (admin only)
- `/stats` — view bot statistics (admin only)

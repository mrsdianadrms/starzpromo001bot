# content.py
# Anniversary events library.
# Format: "MM-DD": {"title": "...", "message": "..."}
# Add as many as you want. The bot will auto-send on matching dates.

ANNIVERSARY_EVENTS = {
    "01-01": {
        "title": "New Year Anniversary Kickoff",
        "message": "🎉 Happy New Year! Today marks the start of our anniversary season. Stay tuned for daily updates all year long."
    },
    "02-14": {
        "title": "Founder's Day",
        "message": "💖 On this day, our journey began. Thank you for being part of our story."
    },
    "03-08": {
        "title": "Community Milestone",
        "message": "🌟 Today we celebrate our community. Every member made this possible."
    },
    "06-15": {
        "title": "Grand Anniversary Day",
        "message": "🎂 Today is our official anniversary! Thank you for growing with us."
    },
    "12-25": {
        "title": "Year-End Celebration",
        "message": "🎄 As the year closes, we celebrate everyone who joined us. Happy holidays!"
    },
}

# Optional: Weekly recurring motivational message.
# Set to None to disable.
WEEKLY_MESSAGE = {
    "title": "Weekly Anniversary Countdown",
    "message": "⏳ Another week closer to our next anniversary milestone. Thank you for staying with us."
}

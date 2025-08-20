from datetime import datetime, timedelta
import json
import os
from utils.common_utils import extract_keywords
from difflib import SequenceMatcher

def load_events():
    file_path = "data/events.json"
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def get_this_week_events(events):
    today = datetime.today()
    start_week = today - timedelta(days=today.weekday())
    end_week = start_week + timedelta(days=6)
    return [
        e for e in events
        if start_week.date() <= datetime.strptime(e["date"], "%Y-%m-%d").date() <= end_week.date()
    ]
# Today’s Events
def get_today_events(events):
    today = datetime.today().date()
    return [e for e in events if datetime.strptime(e["date"], "%Y-%m-%d").date() == today]

# Tomorrow’s Events
def get_tomorrow_events(events):
    tomorrow = datetime.today().date() + timedelta(days=1)
    return [e for e in events if datetime.strptime(e["date"], "%Y-%m-%d").date() == tomorrow]

# Next Week’s Events
def get_next_week_events(events):
    today = datetime.today()
    start = today + timedelta(days=(7 - today.weekday()))  # Next Monday
    end = start + timedelta(days=6)
    return [e for e in events if start.date() <= datetime.strptime(e["date"], "%Y-%m-%d").date() <= end.date()]

# Next Month’s Events
def get_next_month_events(events):
    today = datetime.today()
    next_month = (today.month % 12) + 1
    year = today.year if next_month != 1 else today.year + 1
    return [e for e in events if datetime.strptime(e["date"], "%Y-%m-%d").month == next_month and
                              datetime.strptime(e["date"], "%Y-%m-%d").year == year]

# Search by keywords (fallback)
def search_events(user_input, events):
    keywords = extract_keywords(user_input)
    query = user_input.lower()
    best_score = 0
    best_match = None

    for event in events:
        title = event.get("title", "").lower()
        description = event.get("description", "").lower()
        content = f"{title} {description}"
        keyword_score = sum(1 for kw in keywords if kw in content)
        similarity_score = SequenceMatcher(None, query, content).ratio()
        total_score = keyword_score * 0.6 + similarity_score * 0.4
        if total_score > best_score:
            best_score = total_score
            best_match = event

    if best_match:
        return [best_match]
    return []
def format_events(events):
    return [
        f"📌 **{e['title']}**\n {e['description']}\n Date: {e['date']}"
        for e in events
    ]
# Events in the Next 7 Days (including today)
def get_next_seven_days_events(events):
    today = datetime.today().date()
    end_date = today + timedelta(days=6)
    return [
        e for e in events
        if today <= datetime.strptime(e["date"], "%Y-%m-%d").date() <= end_date
    ]

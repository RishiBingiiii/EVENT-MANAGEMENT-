"""Small shared helpers: countdown formatting and calendar grid building."""

import calendar
from datetime import datetime


def parse_event_datetime(event_date, event_time):
    """Combine an event's date + time strings into a single datetime.
    Falls back to midnight if time is missing/unparseable."""
    time_str = event_time or "00:00"
    try:
        return datetime.strptime(f"{event_date} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        try:
            return datetime.strptime(event_date, "%Y-%m-%d")
        except ValueError:
            return None


def countdown_text(event_date, event_time):
    """Return a short human-readable countdown string, e.g. '🟢 in 3d 4h',
    '🟠 Starting very soon!', or '🔴 Event has ended'."""
    target = parse_event_datetime(event_date, event_time)
    if target is None:
        return ""
    delta = target - datetime.now()
    total_seconds = delta.total_seconds()

    if total_seconds <= 0:
        return "🔴 Event has ended"

    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60

    if days == 0 and hours == 0 and minutes < 30:
        return "🟠 Starting very soon!"
    if days == 0:
        if hours > 0:
            return f"🟡 in {hours}h {minutes}m"
        return f"🟡 in {minutes}m"
    if days <= 7:
        return f"🟢 in {days}d {hours}h"
    return f"🟢 in {days} days"


def build_month_grid(year, month):
    """Return a list of weeks (each a list of 7 date objects, or None for
    out-of-month padding) for the given year/month, Monday-first."""
    cal = calendar.Calendar(firstweekday=0)  # Monday = 0
    weeks = []
    for week in cal.monthdatescalendar(year, month):
        weeks.append([d if d.month == month else None for d in week])
    return weeks


def events_by_date(events):
    """Group a list of event dicts by their event_date string ('YYYY-MM-DD')."""
    grouped = {}
    for ev in events:
        grouped.setdefault(ev["event_date"], []).append(ev)
    return grouped


def format_price(price_rupees):
    """Return 'Free' for 0, else a formatted INR amount."""
    if not price_rupees:
        return "Free"
    return f"₹{price_rupees:,.0f}"

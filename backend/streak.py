"""
backend/streak.py
--------------------
USER-DASHBOARD STREAK FEATURE.

Pure, testable streak computation (`compute_streak`) plus a thin
real-data aggregator (`get_user_streak`) for the Sahay AI User Dashboard
streak indicator.

NO NEW DATABASE TABLE: this reuses the same RLS-scoped, per-user read
functions backend/conversations.py already exposes - list_conversations,
list_mood_events, list_wellness_activity_logs. A user is considered
"active" on a UTC calendar date if any of those three activity sources
has a timestamp on that date. Nothing here writes anything; it is a
read-only aggregation over data that already exists for every other
Sahay AI feature.

VISUAL/CONCEPT NOTE: the uploaded LearnMate AI screenshot was used only
as a reference for WHERE a streak indicator sits and what a "current
streak + this week's status" summary looks like. This module's data
model, function names, and computation are original to Sahay AI and do
not read, import, or duplicate any LearnMate code, table, or branding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


@dataclass
class StreakData:
    current_streak: int
    active_today: bool
    has_any_activity: bool
    last_active_date: date | None
    week_days: list[dict] = field(default_factory=list)  # [{label, status, is_today}]


def _parse_date(raw: str | None) -> date | None:
    """Stored timestamps are UTC (Supabase timestamptz). Returns the UTC
    calendar date, or None for a missing/unparseable value - never
    guessed or defaulted to today."""
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(timezone.utc).date()
    except Exception:  # noqa: BLE001 - one bad timestamp shouldn't break the whole streak
        return None


def _collect_active_dates(conversations: list[dict], mood_events: list[dict], activity_logs: list[dict]) -> set[date]:
    dates: set[date] = set()
    for c in conversations:
        d = _parse_date(c.get("updated_at") or c.get("created_at"))
        if d:
            dates.add(d)
    for m in mood_events:
        d = _parse_date(m.get("created_at"))
        if d:
            dates.add(d)
    for a in activity_logs:
        d = _parse_date(a.get("completed_at"))
        if d:
            dates.add(d)
    return dates


def compute_streak(active_dates: set[date], today: date | None = None) -> StreakData:
    """Given the set of UTC calendar dates on which the user was active,
    computes the current streak ending today (or yesterday, if today
    has no activity yet - a day only "breaks" the streak once it has
    fully passed with no activity). Handles: first activity (a single
    active date -> streak 1), consecutive days, a missed day (streak
    resets to 0 once more than one day has elapsed since the last
    activity), returning after a break (a new streak starts counting
    from the new run of active dates), and zero activity (streak 0,
    has_any_activity False)."""
    today = today or datetime.now(timezone.utc).date()
    has_any = bool(active_dates)
    active_today = today in active_dates
    last_active = max(active_dates) if active_dates else None

    streak = 0
    if has_any and last_active is not None and (today - last_active).days <= 1:
        cursor = today if active_today else today - timedelta(days=1)
        while cursor in active_dates:
            streak += 1
            cursor -= timedelta(days=1)

    week_start = today - timedelta(days=today.weekday())  # Monday of the current week
    week_days = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        if d > today:
            status = "future"
        elif d == today:
            status = "today_active" if active_today else "today_inactive"
        elif d in active_dates:
            status = "completed"
        else:
            status = "missed"
        week_days.append({"label": WEEKDAY_LABELS[i], "status": status, "is_today": d == today})

    return StreakData(
        current_streak=streak,
        active_today=active_today,
        has_any_activity=has_any,
        last_active_date=last_active,
        week_days=week_days,
    )


def get_user_streak(user, conv_db) -> StreakData:
    """Fetches this user's own activity (RLS-scoped, via the same
    backend.conversations functions the rest of the app already uses)
    and computes their real streak. Never fabricates a value: with zero
    stored activity this returns current_streak=0, has_any_activity=False."""
    conversations = conv_db.list_conversations(user)
    mood_events = conv_db.list_mood_events(user, limit=500)
    activity_logs = conv_db.list_wellness_activity_logs(user, limit=500)
    active_dates = _collect_active_dates(conversations, mood_events, activity_logs)
    return compute_streak(active_dates)

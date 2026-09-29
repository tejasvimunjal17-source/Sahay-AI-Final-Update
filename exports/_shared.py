"""
exports/_shared.py
--------------------
PHASE 6 IMPLEMENTATION.

Data-fetching and content-shaping logic shared by exports/pdf.py and
exports/docx.py, so both formats stay consistent in structure and
terminology (per your instruction) without duplicating the "what goes in
a Wellness Reflection Report" decision in two places.

DELIBERATELY SEPARATE from the actual PDF/DOCX rendering calls: every
function here is plain Python (dicts, dataclasses, strings) with zero
dependency on fpdf2 or python-docx, specifically so this logic — the
part that decides WHAT data goes into a report and enforces the privacy/
safety rules around it — can be tested without either rendering library
installed. The two render_*() functions in pdf.py/docx.py are thin
translators from this shared content into library-specific calls.

PRIVACY / SAFETY (see PHASE6_PRE_IMPLEMENTATION_AUDIT.md §8, §6):
- Reads ONLY through backend.conversations's existing RLS-scoped
  functions — never the service-role client, never another user's data.
- Bounded reporting window: 7, 14, or 30 days — NEVER "all time". No
  function in this module accepts or produces an unbounded export.
- UPDATED (report-upgrade task, explicitly requested): the report now
  also carries the user's COMPLETE Companion conversation text for the
  selected period (from the messages table, RLS-scoped, own rows only)
  plus a SEPARATE chatbot-launcher section. The launcher never persists
  to Supabase (see components/chatbot_launcher.py), so that section can
  only contain the current browser session's turns, and only turns
  stamped with the current user's id. The existing conversation summary
  table is kept as-is.
- Never includes: the system prompt, API keys, Supabase keys, or any
  chain-of-thought — none of those are ever fetched by this module in
  the first place (backend.conversations's functions don't expose them
  either), so there's nothing to accidentally leak here.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from backend.auth import AuthUser
from chatbot.mood_analyzer import MOOD_EMOJI

VALID_PERIOD_DAYS = (7, 14, 30)
DEFAULT_PERIOD_DAYS = 30

DISCLAIMER = (
    "This is an AI-generated wellness reflection summary based on your own "
    "activity in Sahay AI. It is NOT a medical assessment, clinical "
    "evaluation, or diagnosis, and Sahay AI is not a therapist, doctor, "
    "psychologist, or psychiatrist. Mood, stress, energy, and sleep values "
    "are self-reported or AI-generated non-clinical signals, not medical "
    "measurements. If you have concerns about your wellbeing, please talk "
    "to a qualified professional or trusted person — see the Human Help "
    "section in the app."
)


@dataclass
class ReportData:
    """Everything a PDF/DOCX builder needs, already shaped and bounded.
    No raw Supabase rows, no unbounded lists, nothing beyond what's
    listed here — see the module docstring for why."""
    generated_at: str
    period_days: int
    period_start: str
    period_end: str
    display_name: str | None
    has_any_data: bool
    conversations_summary: list[dict] = field(default_factory=list)  # [{title, date, message_count}]
    mood_events: list[dict] = field(default_factory=list)  # [{date, mood, sentiment, stress, energy, sleep, source, note}]
    mood_distribution: dict = field(default_factory=dict)  # {mood: count}
    stress_avg: float | None = None
    energy_avg: float | None = None
    sleep_avg: float | None = None
    activities_completed: int = 0
    # Full Companion transcripts: [{title, started, messages: [{ts, role, content}]}]
    companion_transcripts: list[dict] = field(default_factory=list)
    # Launcher chatbot turns (session-only): [{ts (str|None), role, content}]
    chatbot_messages: list[dict] = field(default_factory=list)
    chatbot_note: str = ""
    disclaimer: str = DISCLAIMER


COMPANION_LABEL = "Sahay AI"
CHATBOT_LABEL = "Sahay AI Chatbot"
USER_LABEL = "User"

CHATBOT_SESSION_NOTE = (
    "The Sahay AI chatbot does not save its history to your account. This "
    "section lists only the messages from your current browser session."
)


def _clean_text(value) -> str:
    """Strip characters that no document format can carry (NUL / C0
    control characters other than newline and tab) so one odd stored
    message can't fail a whole export. Text is otherwise untouched."""
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    return "".join(ch for ch in text if ch in "\n\t" or ord(ch) >= 32 and not (0x7F <= ord(ch) <= 0x9F))


def format_timestamp(raw) -> str | None:
    """Stored timestamps are UTC (Supabase timestamptz). Returns a
    human-readable UTC string, or None when missing/unparseable - callers
    print 'time not recorded' rather than inventing one."""
    if not raw:
        return None
    try:
        return _parse_ts(str(raw)).astimezone(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    except Exception:  # noqa: BLE001
        return None


def validate_period_days(period_days: int) -> int:
    if period_days not in VALID_PERIOD_DAYS:
        raise ValueError(f"period_days must be one of {VALID_PERIOD_DAYS}, got {period_days!r}")
    return period_days


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _within_period(items: list[dict], field_name: str, cutoff: datetime) -> list[dict]:
    result = []
    for item in items:
        raw = item.get(field_name)
        if not raw:
            continue
        try:
            ts = _parse_ts(raw)
        except Exception:  # noqa: BLE001 - malformed/missing timestamp, skip rather than crash the report
            continue
        if ts >= cutoff:
            result.append(item)
    return result


def _build_companion_transcripts(user: AuthUser, conv_db, conversations: list[dict], cutoff: datetime) -> list[dict]:
    """Complete stored Companion messages inside the period, grouped by
    conversation, chronological. Own rows only (RLS + user_id filter)."""
    rows = conv_db.list_messages_since(user, cutoff.isoformat())
    titles = {c.get("id"): (c.get("title") or "Untitled conversation") for c in conversations}
    grouped: dict[str, list[dict]] = {}
    for m in rows:
        if m.get("role") not in ("user", "assistant"):
            continue
        grouped.setdefault(m.get("conversation_id"), []).append(m)
    transcripts = []
    for conv_id, msgs in grouped.items():
        msgs.sort(key=lambda m: m.get("created_at") or "")
        transcripts.append({
            "title": titles.get(conv_id, "Untitled conversation"),
            "started": format_timestamp(msgs[0].get("created_at")),
            "_sort": msgs[0].get("created_at") or "",
            "messages": [
                {
                    "ts": format_timestamp(m.get("created_at")),
                    "role": USER_LABEL if m.get("role") == "user" else COMPANION_LABEL,
                    "content": _clean_text(m.get("content")),
                }
                for m in msgs
            ],
        })
    transcripts.sort(key=lambda t: t["_sort"])
    for t in transcripts:
        t.pop("_sort", None)
    return transcripts


def _shape_chatbot_history(history: list[dict] | None, owner_id: str | None, cutoff: datetime | None) -> list[dict]:
    """Launcher-chatbot turns from THIS browser session. For a signed-in
    user only turns stamped with that same user id are used - sign_out()
    does not clear this session list, so without the stamp check a second
    account signing in on the same browser session could see the first
    account's chatbot turns. Turns without a stamp are excluded for a
    signed-in report (fail closed). Timestamps come from the turn's own
    'ts' field when present; older turns have none and are labelled as
    such - never fabricated."""
    shaped = []
    for turn in history or []:
        role = turn.get("role")
        if role not in ("user", "assistant") or not turn.get("content"):
            continue
        if owner_id is not None and turn.get("uid") != owner_id:
            continue
        ts_raw = turn.get("ts")
        if cutoff is not None and ts_raw:
            try:
                if _parse_ts(ts_raw) < cutoff:
                    continue
            except Exception:  # noqa: BLE001
                pass
        shaped.append({
            "ts": format_timestamp(ts_raw),
            "role": USER_LABEL if role == "user" else CHATBOT_LABEL,
            "content": _clean_text(turn.get("content")),
        })
    return shaped


def build_report_data(
    user: AuthUser,
    conv_db,
    period_days: int = DEFAULT_PERIOD_DAYS,
    display_name: str | None = None,
    chatbot_history: list[dict] | None = None,
) -> ReportData:
    """Fetches and shapes everything needed for a Wellness Reflection
    Report, bounded to the last `period_days` days. Raises ValueError for
    an out-of-range period. Never raises for "no data found" — returns a
    ReportData with has_any_data=False instead, so the caller (the
    Reports page) can show a friendly "not enough data" state rather
    than a crash or an empty-looking report."""
    period_days = validate_period_days(period_days)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=period_days)

    all_conversations = conv_db.list_conversations(user)
    conversations_in_period = _within_period(all_conversations, "created_at", cutoff)
    conversations_summary = []
    for c in conversations_in_period:
        try:
            messages = conv_db.list_messages(user, c["id"])
        except Exception:  # noqa: BLE001 - one bad conversation shouldn't break the whole report
            messages = []
        conversations_summary.append({
            "title": c.get("title") or "Untitled conversation",
            "date": c.get("created_at", "")[:10],
            "message_count": len(messages),
        })

    all_mood_events = conv_db.list_mood_events(user, limit=500)
    mood_events_in_period = _within_period(all_mood_events, "created_at", cutoff)
    mood_events_shaped = [
        {
            "date": m.get("created_at", "")[:16].replace("T", " "),
            "mood": m.get("mood"),
            "emoji": MOOD_EMOJI.get(m.get("mood"), ""),
            "sentiment": m.get("sentiment"),
            "stress": m.get("stress_level"),
            "energy": m.get("energy_level"),
            "sleep": m.get("sleep_quality"),
            "source": "Check-in" if m.get("source") == "checkin" else "Chat",
            "note": m.get("note"),
        }
        for m in mood_events_in_period
    ]

    mood_distribution = dict(Counter(m["mood"] for m in mood_events_shaped if m.get("mood")))

    def _avg(field_key: str) -> float | None:
        vals = [m[field_key] for m in mood_events_shaped if m.get(field_key) is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    all_activity_logs = conv_db.list_wellness_activity_logs(user, limit=500)
    activities_in_period = _within_period(all_activity_logs, "completed_at", cutoff)

    companion_transcripts = _build_companion_transcripts(user, conv_db, all_conversations, cutoff)
    chatbot_messages = _shape_chatbot_history(chatbot_history, user.id, cutoff)

    has_any_data = bool(
        conversations_summary or mood_events_shaped or activities_in_period
        or companion_transcripts or chatbot_messages
    )

    return ReportData(
        generated_at=now.strftime("%d %B %Y, %H:%M UTC"),
        period_days=period_days,
        period_start=cutoff.strftime("%d %B %Y"),
        period_end=now.strftime("%d %B %Y"),
        display_name=display_name,
        has_any_data=has_any_data,
        conversations_summary=conversations_summary,
        mood_events=mood_events_shaped,
        mood_distribution=mood_distribution,
        stress_avg=_avg("stress"),
        energy_avg=_avg("energy"),
        sleep_avg=_avg("sleep"),
        activities_completed=len(activities_in_period),
        companion_transcripts=companion_transcripts,
        chatbot_messages=chatbot_messages,
        chatbot_note=CHATBOT_SESSION_NOTE,
    )


def build_demo_report_data(
    chat_history: list[dict],
    period_days: int = DEFAULT_PERIOD_DAYS,
    companion_history: list[dict] | None = None,
    chatbot_history: list[dict] | None = None,
) -> ReportData:
    """Demo Mode variant: builds a report from the CURRENT SESSION's
    in-memory chat history only — never touches Supabase, never persists
    anything. Per the approved Phase 6 decision: Demo Mode gets a small,
    clearly-labeled sample export, not a message telling the user to
    sign in. Mood/stress/energy/sleep data is never included here, since
    Demo Mode never persists mood_events regardless of chat content."""
    now = datetime.now(timezone.utc)
    message_count = len([m for m in chat_history if m.get("role") in ("user", "assistant")])
    demo_companion = []
    if companion_history:
        demo_msgs = [
            {"ts": format_timestamp(t.get("ts")), "role": USER_LABEL if t.get("role") == "user" else COMPANION_LABEL,
             "content": _clean_text(t.get("content"))}
            for t in companion_history if t.get("role") in ("user", "assistant") and t.get("content")
        ]
        if demo_msgs:
            demo_companion = [{"title": "Demo Mode conversation (sample)", "started": demo_msgs[0]["ts"], "messages": demo_msgs}]
    demo_chatbot = _shape_chatbot_history(chatbot_history, None, None)
    return ReportData(
        generated_at=now.strftime("%d %B %Y, %H:%M UTC"),
        period_days=period_days,
        period_start="(Demo Mode — current session only)",
        period_end=now.strftime("%d %B %Y"),
        display_name=None,
        has_any_data=message_count > 0 or bool(demo_chatbot),
        conversations_summary=[{"title": "Demo Mode conversation (sample)", "date": now.strftime("%Y-%m-%d"), "message_count": message_count}] if message_count else [],
        mood_events=[],
        mood_distribution={},
        companion_transcripts=demo_companion,
        chatbot_messages=demo_chatbot,
        chatbot_note=CHATBOT_SESSION_NOTE,
        disclaimer=DISCLAIMER + (
            " This export is SAMPLE DATA from your current Demo Mode session only "
            "— it is not saved anywhere and does not represent a persisted wellness "
            "history. Sign in to build and export a real history over time."
        ),
    )

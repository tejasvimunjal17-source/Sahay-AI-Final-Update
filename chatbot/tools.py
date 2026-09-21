"""
chatbot/tools.py
------------------
PHASE 3 IMPLEMENTATION (Agentic AI upgrade — controlled tool registry).

Defines a fixed, explicitly allowlisted set of READ-ONLY tools that a
future orchestration/tool-calling phase will be able to invoke. This
module does NOT wire anything to an LLM: backend/openrouter_client.py
and chatbot/response_generator.py are both untouched by this phase, no
`tools=`/`tool_choice=` parameter exists anywhere yet, and nothing here
is reachable from a model's output. This is purely the safe layer a
later, separately-approved phase will connect.

SECURITY MODEL:
- Every tool reuses an EXISTING backend/content function — no new
  database-access logic is written here.
- Every per-user tool goes through backend/conversations.py, which
  uses ONLY the anon-key, RLS-scoped client
  (backend.auth.get_client_for_current_user()) — this module never
  imports backend.supabase_admin_client, directly or indirectly.
- No tool accepts a table name, a raw query, or a raw user_id string —
  per-user tools take a full backend.auth.AuthUser object (or None for
  Demo Mode), exactly like backend/conversations.py already requires.
- No destructive/write tool exists in this phase.
- TOOL_REGISTRY is a fixed, literal dict — every key and value is
  written directly in this file's source. call_tool() below looks up
  ONLY this dict. There is no getattr(), no eval(), no dynamic import,
  and no way to make an additional function callable without editing
  this file.
- Every per-user tool returns a neutral, successful, empty-shaped
  result when `user is None` (Demo Mode) WITHOUT ever calling
  backend/conversations.py — Demo Mode never touches Supabase, in this
  module exactly as everywhere else in the app.
- Raw free-text is never included in any tool result in this phase:
  mood-event `note` is excluded from get_user_checkins, and
  get_recent_conversation_summary returns conversation-level metadata
  ONLY — no message content of any kind (Option B, approved for
  Phase 3 — see PHASE3 audit).
- Every tool result is a plain dict shaped
  {"ok": bool, "tool": str, "data": ..., "error": str | None} — no
  internal exception, traceback, or implementation detail is ever
  placed in "error" (only a short, fixed code string).

KNOWN ARCHITECTURAL TRADE-OFF (documented, not fixed, in this phase):
recommend_relaxation_activity(), recommend_resource(), and
find_human_support() import static content lists (ACTIVITIES,
CATEGORIES, NORMAL_SUPPORT) directly from pages/relaxation.py,
pages/resources.py, and pages/human_help.py rather than from a shared
content/ module. This makes chatbot/ depend on pages/, which is
backwards from the rest of the app's dependency direction (pages/
normally depends on chatbot/backend/, not vice versa). It is NOT a
circular import — none of those three page modules import anything
from chatbot/ — so there is no functional risk, only a structural one.
Approved as a deliberate, temporary trade-off to avoid touching those
three page files in this phase; extracting the three lists into
content/ (matching the existing content/crisis_resources.py pattern)
remains a clean, low-risk future refactor, not undertaken here.

PHASE 5 OPTION B ADDITION (Navigator page-navigation suggestions):
open_page() follows the same content-only pattern as
recommend_relaxation_activity()/recommend_resource() — it validates
against components.sidebar.ALL_PAGE_KEYS/NAV_GROUPS (read-only import,
same "chatbot/ depends on pages/-adjacent modules" trade-off noted
above, extended to components/) and returns data only. It does NOT
import streamlit, does NOT touch st.session_state, and does NOT call
st.rerun() — it cannot cause a navigation by itself. All six Phase 3
tools above are unmodified by this addition.
"""

from __future__ import annotations

from typing import Callable

from backend.auth import AuthUser
from backend.logging_config import get_logger
from chatbot.mood_analyzer import VALID_MOODS, MOOD_SUGGESTIONS
from content.crisis_resources import CRISIS_RESOURCES

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Bounds — every caller-supplied numeric argument is clamped to one of
# these before it ever reaches a backend call. No unbounded value is
# ever passed to a .limit(...) call.
# ---------------------------------------------------------------------------
_DEFAULT_CHECKIN_LIMIT = 20
_MAX_CHECKIN_LIMIT = 50
_DEFAULT_WELLNESS_LOG_LIMIT = 50
_MAX_WELLNESS_LOG_LIMIT = 100


def _ok(tool: str, data) -> dict:
    return {"ok": True, "tool": tool, "data": data, "error": None}


def _error(tool: str, error_code: str) -> dict:
    return {"ok": False, "tool": tool, "data": None, "error": error_code}


def _clamp(value: int, default: int, maximum: int) -> int:
    """Validated, typed numeric bound. Rejects non-int, bool (a bool is
    technically an int in Python — explicitly excluded), and <=0 values
    by silently falling back to `default` rather than raising, since a
    tool argument's job is to degrade safely, not to crash a turn."""
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        return default
    return min(value, maximum)


# ---------------------------------------------------------------------------
# 1. get_user_checkins — READ-ONLY
# ---------------------------------------------------------------------------

def get_user_checkins(user: AuthUser | None = None, limit: int = _DEFAULT_CHECKIN_LIMIT) -> dict:
    """Recent non-clinical mood check-ins for the authenticated caller.

    Reuses backend.conversations.list_mood_events — no new data-access
    logic. Demo Mode (user is None) returns an empty, successful result
    without ever touching Supabase.

    Excludes id, user_id, conversation_id, and the free-text `note`
    field — only structured, already non-clinical fields are returned."""
    tool_name = "get_user_checkins"
    if user is None:
        return _ok(tool_name, [])

    limit = _clamp(limit, _DEFAULT_CHECKIN_LIMIT, _MAX_CHECKIN_LIMIT)
    try:
        from backend import conversations as conv_db
        events = conv_db.list_mood_events(user, limit=limit)
    except Exception:  # noqa: BLE001 - never leak internals through a tool result
        logger.exception("get_user_checkins: backend lookup failed")
        return _error(tool_name, "lookup_failed")

    shaped = [
        {
            "mood": e.get("mood"),
            "sentiment": e.get("sentiment"),
            "confidence": e.get("confidence"),
            "risk_level": e.get("risk_level"),
            "stress_level": e.get("stress_level"),
            "energy_level": e.get("energy_level"),
            "sleep_quality": e.get("sleep_quality"),
            "source": e.get("source"),
            "created_at": e.get("created_at"),
        }
        for e in events
    ]
    return _ok(tool_name, shaped)


# ---------------------------------------------------------------------------
# 2. get_recent_conversation_summary — READ-ONLY
# ---------------------------------------------------------------------------

def get_recent_conversation_summary(user: AuthUser | None = None) -> dict:
    """Conversation-level METADATA ONLY for the caller's single
    most-recently-updated conversation. Per approved Phase 3 scope
    (Option B): no message content of any kind is read or returned —
    only has_conversation / title / message_count / updated_at.

    Reuses backend.conversations.list_conversations (already ordered by
    updated_at desc — no new query logic) and list_messages (used ONLY
    to compute a count via len(); no message field, including
    `content`, is ever accessed). Demo Mode returns a neutral
    'no conversation' result without touching Supabase."""
    tool_name = "get_recent_conversation_summary"
    empty = {"has_conversation": False, "title": None, "message_count": 0, "updated_at": None}
    if user is None:
        return _ok(tool_name, empty)

    try:
        from backend import conversations as conv_db
        conversations = conv_db.list_conversations(user)  # already ordered by updated_at desc
        if not conversations:
            return _ok(tool_name, empty)
        latest = conversations[0]
        # Reused only to compute a count — no message field is read.
        messages = conv_db.list_messages(user, latest["id"])
    except Exception:  # noqa: BLE001
        logger.exception("get_recent_conversation_summary: backend lookup failed")
        return _error(tool_name, "lookup_failed")

    return _ok(tool_name, {
        "has_conversation": True,
        "title": latest.get("title"),
        "message_count": len(messages),
        "updated_at": latest.get("updated_at"),
    })


# ---------------------------------------------------------------------------
# 3. get_wellness_progress — READ-ONLY
# ---------------------------------------------------------------------------

def get_wellness_progress(user: AuthUser | None = None, limit: int = _DEFAULT_WELLNESS_LOG_LIMIT) -> dict:
    """Recent completed wellness activities (activity key + completion
    time only). Reuses backend.conversations.list_wellness_activity_logs.
    Demo Mode returns an empty, successful result without touching
    Supabase."""
    tool_name = "get_wellness_progress"
    if user is None:
        return _ok(tool_name, [])

    limit = _clamp(limit, _DEFAULT_WELLNESS_LOG_LIMIT, _MAX_WELLNESS_LOG_LIMIT)
    try:
        from backend import conversations as conv_db
        logs = conv_db.list_wellness_activity_logs(user, limit=limit)
    except Exception:  # noqa: BLE001
        logger.exception("get_wellness_progress: backend lookup failed")
        return _error(tool_name, "lookup_failed")

    shaped = [{"activity_key": l.get("activity_key"), "completed_at": l.get("completed_at")} for l in logs]
    return _ok(tool_name, shaped)


# ---------------------------------------------------------------------------
# 4. recommend_relaxation_activity — READ-ONLY, content-only
# ---------------------------------------------------------------------------

def recommend_relaxation_activity(user: AuthUser | None = None, mood: str | None = None) -> dict:
    """Recommends an EXISTING activity from pages.relaxation.ACTIVITIES
    — never invents one. `user` is accepted for interface uniformity
    with the other tools but is NOT used: this tool touches no
    per-user data or Supabase, so behavior is identical in Demo Mode
    and authenticated use.

    Uses the same mood -> activity_key mapping already defined in
    chatbot.mood_analyzer.MOOD_SUGGESTIONS (the same table the existing
    suggestion card already uses), so recommendations stay consistent
    with what the app suggests elsewhere. Unrecognized/None mood, or a
    mood with no mapped activity (e.g. "Happy"), returns data=None
    rather than guessing."""
    tool_name = "recommend_relaxation_activity"
    if mood not in VALID_MOODS:
        return _ok(tool_name, None)

    mapped = MOOD_SUGGESTIONS.get(mood)
    activity_key = mapped.get("activity_key") if mapped else None
    if not activity_key:
        return _ok(tool_name, None)

    from pages.relaxation import ACTIVITIES  # existing definitions, not duplicated — see module docstring
    activity = next((a for a in ACTIVITIES if a["key"] == activity_key), None)
    if activity is None:
        return _ok(tool_name, None)

    return _ok(tool_name, {
        "activity_key": activity["key"],
        "title": activity["title"],
        "duration": activity["duration"],
        "description": activity["description"],
    })


# ---------------------------------------------------------------------------
# 5. recommend_resource — READ-ONLY, content-only
# ---------------------------------------------------------------------------

def recommend_resource(user: AuthUser | None = None, topic: str | None = None) -> dict:
    """Recommends an EXISTING category from pages.resources.CATEGORIES
    by a simple, case-insensitive substring match on the category
    label — never invents a resource. `user` accepted for interface
    uniformity, not used (content-only, no Supabase access). None/blank
    `topic`, or no match, returns data=None."""
    tool_name = "recommend_resource"
    if not isinstance(topic, str) or not topic.strip():
        return _ok(tool_name, None)

    from pages.resources import CATEGORIES  # existing definitions, not duplicated — see module docstring
    needle = topic.strip().lower()
    match = next((c for c in CATEGORIES if needle in c[0].lower()), None)
    if match is None:
        return _ok(tool_name, None)

    label, _icon, desc, tip, activity_key = match
    return _ok(tool_name, {
        "label": label,
        "description": desc,
        "tip": tip,
        "related_activity_key": activity_key,
    })


# ---------------------------------------------------------------------------
# 6. find_human_support — READ-ONLY, content-only
# ---------------------------------------------------------------------------

def find_human_support(user: AuthUser | None = None) -> dict:
    """Points to the existing Human Help page and its non-crisis support
    options (pages.human_help.NORMAL_SUPPORT), plus any verified crisis
    resources (content.crisis_resources.CRISIS_RESOURCES — empty-safe,
    never invents a hotline). `user` accepted for interface uniformity,
    not used.

    Deliberately EXCLUDES pages.human_help.URGENT_SUPPORT's wording:
    crisis-situation messaging is owned exclusively by
    chatbot/safety.py's deterministic crisis handling — this tool must
    never hand a future model material it could paraphrase into ad hoc
    crisis advice."""
    tool_name = "find_human_support"
    from pages.human_help import NORMAL_SUPPORT  # existing definitions, not duplicated — see module docstring

    return _ok(tool_name, {
        "page_key": "human_help",
        "normal_support_options": [{"who": who, "when": when} for who, when in NORMAL_SUPPORT],
        "crisis_resources": list(CRISIS_RESOURCES),
    })


# ---------------------------------------------------------------------------
# 7. open_page — READ-ONLY, content-only (PHASE 5 OPTION B addition)
# ---------------------------------------------------------------------------

def open_page(user: AuthUser | None = None, page_key: str | None = None) -> dict:
    """READ-ONLY, content-only (no user/Supabase access, no Streamlit
    import, no session-state mutation of any kind). `user` accepted for
    interface uniformity, not used.

    Validates `page_key` strictly against the real, current
    components.sidebar.ALL_PAGE_KEYS — the exact same list that drives
    the sidebar navigation and streamlit_app.py's page router. Admin is
    never reachable this way: it isn't and has never been a member of
    ALL_PAGE_KEYS (a structurally separate ?admin=1 flow — see
    streamlit_app.py).

    Returns ONLY a data description of the suggested destination — it
    NEVER writes st.session_state and NEVER calls st.rerun(). Whether
    and when to actually navigate is entirely the UI layer's decision,
    made only after the student explicitly confirms (see
    components/chatbot_launcher.py) — this function cannot cause a
    navigation by itself, by design.

    The returned `label` always comes from the real navigation metadata
    (components.sidebar.NAV_GROUPS) — never from the model's own text —
    so a compromised or hallucinated tool argument can, at worst, name a
    real existing page; it can never fabricate a misleading label for
    it. An invalid/unrecognized page_key returns data=None, exactly
    like recommend_relaxation_activity/recommend_resource already do
    for unrecognized input — never invents a page."""
    tool_name = "open_page"
    from components.sidebar import ALL_PAGE_KEYS, NAV_GROUPS  # existing definitions, not duplicated

    if not isinstance(page_key, str) or page_key not in ALL_PAGE_KEYS:
        return _ok(tool_name, None)

    label = next(
        (label for _group, items in NAV_GROUPS for label, key in items if key == page_key),
        page_key,
    )
    return _ok(tool_name, {"page_key": page_key, "label": label})


# ---------------------------------------------------------------------------
# Controlled, allowlisted registry.
#
# Fixed, literal dict — every key and value is written explicitly in
# this file. No getattr(), no introspection, no dynamic import. There
# is no way to make an additional function callable without editing
# this source file.
#
# NOT YET CONNECTED TO ANY LLM CALL. backend/openrouter_client.py and
# chatbot/response_generator.py are both unmodified by this phase.
# call_tool() exists so a later, separately-approved phase has a
# single, already-hardened dispatch point to wire up.
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, Callable[..., dict]] = {
    "get_user_checkins": get_user_checkins,
    "get_recent_conversation_summary": get_recent_conversation_summary,
    "get_wellness_progress": get_wellness_progress,
    "recommend_relaxation_activity": recommend_relaxation_activity,
    "recommend_resource": recommend_resource,
    "find_human_support": find_human_support,
    "open_page": open_page,
}


def call_tool(tool_name: str, *, user: AuthUser | None = None, **kwargs) -> dict:
    """Single controlled entry point for invoking a registered tool by
    name — looks up ONLY the fixed TOOL_REGISTRY dict above. NOT wired
    to any LLM in this phase (see module docstring).

    An unknown tool name, a bad argument, or any unexpected exception
    all degrade to a sanitized {"ok": False, ...} result — this
    function never raises and never places an internal exception
    message or traceback into the result."""
    func = TOOL_REGISTRY.get(tool_name)
    if func is None:
        return _error(tool_name, "unknown_tool")
    try:
        return func(user=user, **kwargs)
    except TypeError as exc:
        logger.warning("call_tool: invalid arguments for %r: %s", tool_name, exc)
        return _error(tool_name, "invalid_arguments")
    except Exception:  # noqa: BLE001 - never leak internals through a tool result
        logger.exception("call_tool: unexpected error running %r", tool_name)
        return _error(tool_name, "tool_execution_failed")

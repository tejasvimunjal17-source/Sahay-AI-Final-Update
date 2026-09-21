"""
backend/admin_data.py
------------------------
PHASE 7 IMPLEMENTATION.

Aggregate-only admin queries via the service-role client. This is the
SECOND legitimate service-role use case in the whole project (the first
being backend/audit_log.py) — every function here returns counts,
distributions, or short non-content metadata, NEVER a specific user's
conversation/message text. That rule is enforced by what these functions
select, not by a filter applied after the fact: none of them ever
`select("content")` from `messages`.

Every function takes an already-authenticated AdminUser as its first
parameter — not because the query itself checks it (the service-role
client bypasses RLS by design), but so that every call site is visibly,
textually tied to "an admin is asking for this," making it easy to grep
for any accidental use outside an admin-gated code path. This mirrors
the AuthUser-first-parameter convention already established in
backend/conversations.py for students.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from backend.admin_auth import AdminUser
from backend.audit_log import log_event, EVENT_ROLE_CHANGED
from backend.supabase_admin_client import get_admin_client


def _require_admin(admin: AdminUser) -> None:
    if not isinstance(admin, AdminUser):
        raise TypeError("admin_data functions require a verified AdminUser — see backend.admin_auth.get_current_admin()")


# ---------------------------------------------------------------------------
# Usage analytics
# ---------------------------------------------------------------------------

def get_usage_summary(admin: AdminUser, days: int = 30) -> dict:
    """Total users, active users (signed in / created content in the
    window), total conversations, conversations-by-day — all counts,
    never row content."""
    _require_admin(admin)
    client = get_admin_client()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    profiles = client.table("profiles").select("id, created_at").execute().data or []
    conversations = client.table("conversations").select("id, user_id, created_at").execute().data or []

    conversations_in_window = [c for c in conversations if c.get("created_at", "") >= cutoff]
    active_user_ids = {c["user_id"] for c in conversations_in_window}

    by_day = Counter(c["created_at"][:10] for c in conversations_in_window if c.get("created_at"))

    return {
        "total_users": len(profiles),
        "active_users": len(active_user_ids),
        "total_conversations": len(conversations),
        "conversations_in_window": len(conversations_in_window),
        "conversations_by_day": dict(sorted(by_day.items())),
        "window_days": days,
    }


def get_language_usage(admin: AdminUser) -> dict:
    """Distribution of profiles.preferred_language — a count per
    language, never tied back to a specific user in the returned shape."""
    _require_admin(admin)
    client = get_admin_client()
    profiles = client.table("profiles").select("preferred_language").execute().data or []
    return dict(Counter(p.get("preferred_language") or "unspecified" for p in profiles))


# ---------------------------------------------------------------------------
# Mood trend analytics
# ---------------------------------------------------------------------------

def get_mood_distribution(admin: AdminUser, days: int = 30) -> dict:
    """Aggregate mood counts across ALL users in the window — never
    broken out per-user, never including note/content fields."""
    _require_admin(admin)
    client = get_admin_client()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    events = client.table("mood_events").select("mood, created_at").execute().data or []
    in_window = [e for e in events if e.get("created_at", "") >= cutoff and e.get("mood")]
    return dict(Counter(e["mood"] for e in in_window))


# ---------------------------------------------------------------------------
# Wellness activity usage
# ---------------------------------------------------------------------------

def get_activity_usage(admin: AdminUser, days: int = 30) -> dict:
    _require_admin(admin)
    client = get_admin_client()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    logs = client.table("wellness_activity_logs").select("activity_key, completed_at").execute().data or []
    in_window = [l for l in logs if l.get("completed_at", "") >= cutoff]
    return dict(Counter(l["activity_key"] for l in in_window if l.get("activity_key")))


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

def list_users(admin: AdminUser, limit: int = 200) -> list[dict]:
    """Profile summaries only — id, display_name, role, language,
    created_at. Never conversation content, never mood note text."""
    _require_admin(admin)
    client = get_admin_client()
    resp = client.table("profiles").select("id, display_name, role, preferred_language, onboarding_complete, created_at").order("created_at", desc=True).limit(limit).execute()
    return resp.data or []


def set_user_role(admin: AdminUser, target_user_id: str, role: str) -> None:
    """The ONLY code path in this entire project that can change
    profiles.role — deliberately gated behind an already-verified
    AdminUser, using the service-role client, which is the one write
    path 003_role_protection.sql's trigger permits (auth.role() =
    'service_role'). A student's own client can never reach this
    function or this trigger-bypass path.

    PHASE 10A: a successful change is now audit-logged via
    backend.audit_log.log_event() — additive only. Authorization
    (_require_admin), role validation, and the update query itself are
    unchanged. Logging happens AFTER the update call, so a denied
    (_require_admin raises) or invalid-role (ValueError, raised above)
    call never reaches this line and can never produce a misleading
    "success" audit entry. log_event() is best-effort and never raises
    (see its own docstring), so a logging failure cannot roll back or
    mask the already-committed role change. `target` follows the
    existing short-reference convention (e.g. today's `target="google_oauth"`/
    masked-email usage in backend/auth.py) — no new column, no raw
    profile data, no credentials."""
    _require_admin(admin)
    if role not in ("student", "admin"):
        raise ValueError(f"Invalid role: {role!r}")
    client = get_admin_client()
    client.table("profiles").update({"role": role}).eq("id", target_user_id).execute()
    log_event(
        actor_type="admin",
        action=EVENT_ROLE_CHANGED,
        actor_id=admin.id,
        target=f"profile:{target_user_id}:role={role}",
    )


# ---------------------------------------------------------------------------
# Feedback management
# ---------------------------------------------------------------------------

def get_feedback_summary(admin: AdminUser, limit: int = 100) -> dict:
    """Aggregate rating distribution + a bounded list of recent messages.
    Message text IS shown to admins here — unlike conversation content,
    feedback is explicitly submitted BY the user FOR the app's
    maintainers to read, which is a fundamentally different privacy
    posture than a private wellness conversation."""
    _require_admin(admin)
    client = get_admin_client()
    resp = client.table("feedback").select("rating, message, created_at").order("created_at", desc=True).limit(limit).execute()
    rows = resp.data or []
    all_ratings = [r["rating"] for r in rows if r.get("rating") is not None]
    rating_counts = Counter(all_ratings)
    avg_rating = round(sum(all_ratings) / len(all_ratings), 2) if all_ratings else None
    return {
        "recent": rows,
        "rating_distribution": dict(sorted(rating_counts.items())),
        "average_rating": avg_rating,
        "total_count": len(rows),
    }


# ---------------------------------------------------------------------------
# Safety event monitoring
# ---------------------------------------------------------------------------

def get_safety_event_summary(admin: AdminUser, days: int = 30) -> dict:
    """Counts by category/action only — NEVER message content (the table
    itself never stores it — see 013_safety_events.sql)."""
    _require_admin(admin)
    client = get_admin_client()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    events = client.table("safety_events").select("category, action, created_at").execute().data or []
    in_window = [e for e in events if e.get("created_at", "") >= cutoff]
    return {
        "total_in_window": len(in_window),
        "by_category": dict(Counter(e["category"] for e in in_window if e.get("category"))),
        "by_action": dict(Counter(e["action"] for e in in_window if e.get("action"))),
        "window_days": days,
    }


# ---------------------------------------------------------------------------
# System health / configuration (no secrets, ever)
# ---------------------------------------------------------------------------

def get_configuration_status() -> dict:
    """Boolean-only status of each integration — confirms something is
    CONFIGURED, never reveals the value of a key or URL."""
    from config import SUPABASE_USER_CONFIG, SUPABASE_ADMIN_CONFIG, OPENROUTER_CONFIG, GOOGLE_OAUTH_CONFIG
    return {
        "supabase_user_configured": SUPABASE_USER_CONFIG.is_configured,
        "supabase_admin_configured": SUPABASE_ADMIN_CONFIG.is_configured,
        "openrouter_configured": OPENROUTER_CONFIG.is_configured,
        "google_oauth_configured": GOOGLE_OAUTH_CONFIG.is_configured,
    }

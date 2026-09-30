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


# ---------------------------------------------------------------------------
# PART 1 ADMIN UPGRADE (additive, read-only) — Dashboard overview + per-user
# activity counts. Nothing above this line was changed. Every function here
# selects only ids, counts, or timestamps — never `messages.content`,
# `mood_events.note`/`mood`, or any other private text.
# ---------------------------------------------------------------------------

def _count_rows(client, table: str, *, since: str | None = None, since_column: str = "created_at",
                user_id: str | None = None) -> int | None:
    """Exact row count via PostgREST's count header (no row data transferred).
    Returns None — never a fabricated 0 — if the count can't be read, so the
    UI can show "—" instead of a misleading number."""
    try:
        query = client.table(table).select("id", count="exact")
        if since is not None:
            query = query.gte(since_column, since)
        if user_id is not None:
            query = query.eq("user_id", user_id)
        result = query.limit(1).execute()
        return result.count
    except Exception:  # noqa: BLE001 - one unreadable table must not blank the whole dashboard
        return None


def _latest_timestamp(client, table: str, column: str, user_id: str) -> str | None:
    try:
        rows = (
            client.table(table).select(column).eq("user_id", user_id)
            .order(column, desc=True).limit(1).execute().data or []
        )
        return rows[0].get(column) if rows else None
    except Exception:  # noqa: BLE001
        return None


def get_dashboard_overview(admin: AdminUser, days: int = 30) -> dict:
    """Extra Dashboard signals derived only from existing tables:
    registrations (profiles), volume counts for messages / mood check-ins /
    wellness activities / feedback / safety events, and the newest
    registrations (display name + join date only — no email, no ids)."""
    _require_admin(admin)
    client = get_admin_client()
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=days)).isoformat()

    profiles = (
        client.table("profiles")
        .select("id, display_name, role, onboarding_complete, created_at")
        .order("created_at", desc=True).execute().data or []
    )
    cutoff_7d = (now - timedelta(days=7)).isoformat()
    day_labels = [(now - timedelta(days=i)).date().isoformat() for i in range(13, -1, -1)]
    by_day = Counter((p.get("created_at") or "")[:10] for p in profiles)

    return {
        "window_days": days,
        "total_users": len(profiles),
        "admin_role_users": sum(1 for p in profiles if p.get("role") == "admin"),
        "onboarded_users": sum(1 for p in profiles if p.get("onboarding_complete")),
        "new_users_7d": sum(1 for p in profiles if (p.get("created_at") or "") >= cutoff_7d),
        "new_users_in_window": sum(1 for p in profiles if (p.get("created_at") or "") >= cutoff),
        # zero-days are real zeros (no profile was created that day)
        "signups_last_14_days": {d: by_day.get(d, 0) for d in day_labels},
        "recent_registrations": [
            {"display_name": p.get("display_name") or "(no display name)",
             "created_at": (p.get("created_at") or "")[:10]}
            for p in profiles[:5]
        ],
        "totals": {
            "messages": _count_rows(client, "messages"),
            "mood_checkins_and_chat_moods": _count_rows(client, "mood_events"),
            "wellness_activities_completed": _count_rows(client, "wellness_activity_logs", since_column="completed_at"),
            "feedback": _count_rows(client, "feedback"),
            "safety_events": _count_rows(client, "safety_events"),
        },
        "in_window": {
            "messages": _count_rows(client, "messages", since=cutoff),
            "mood_events": _count_rows(client, "mood_events", since=cutoff),
            "wellness_activities_completed": _count_rows(client, "wellness_activity_logs", since=cutoff, since_column="completed_at"),
            "feedback": _count_rows(client, "feedback", since=cutoff),
            "safety_events": _count_rows(client, "safety_events", since=cutoff),
        },
    }


def get_user_activity_summary(admin: AdminUser, target_user_id: str) -> dict:
    """Engagement COUNTS + last-activity timestamp for one profile.
    Deliberately excludes: message/conversation text, mood values, and
    per-user safety-event data (safety monitoring stays aggregate-only)."""
    _require_admin(admin)
    client = get_admin_client()
    stamps = [
        _latest_timestamp(client, "conversations", "updated_at", target_user_id),
        _latest_timestamp(client, "messages", "created_at", target_user_id),
        _latest_timestamp(client, "mood_events", "created_at", target_user_id),
        _latest_timestamp(client, "wellness_activity_logs", "completed_at", target_user_id),
    ]
    stamps = [s for s in stamps if s]
    return {
        "conversations": _count_rows(client, "conversations", user_id=target_user_id),
        "messages": _count_rows(client, "messages", user_id=target_user_id),
        "mood_checkins": _count_rows(client, "mood_events", user_id=target_user_id),
        "wellness_activities": _count_rows(client, "wellness_activity_logs", user_id=target_user_id),
        "feedback_submitted": _count_rows(client, "feedback", user_id=target_user_id),
        "last_activity": max(stamps) if stamps else None,
    }


# ---------------------------------------------------------------------------
# PART 2 ADMIN UPGRADE (additive, read-only) — Database overview.
# Nothing above this line was changed. The registry below is a FIXED,
# hand-written allow-list mirroring database/migrations/*.sql. No table or
# column name ever comes from user input, so this cannot become a generic
# query tool. Tables holding private text or credentials are count-only.
# ---------------------------------------------------------------------------

# name -> (category, purpose, access, timestamp column, preview columns | None)
# preview columns None  => metadata/counts only, raw records are never shown.
# `user_id` is deliberately absent from every preview so rows can't be tied
# to a student, and private text (message content, mood values/notes,
# feedback text) is never selected.
DB_TABLE_REGISTRY: dict[str, dict] = {
    "profiles": {
        "category": "Accounts", "timestamp": "created_at",
        "purpose": "One row per student/admin-role account: display name, language, role, onboarding flag.",
        "access": "User RLS (own row) + service-role for admin views",
        "preview": ["display_name", "role", "preferred_language", "onboarding_complete", "created_at", "updated_at"],
    },
    "admin_users": {
        "category": "Accounts", "timestamp": "created_at",
        "purpose": "Separate admin-panel login accounts.",
        "access": "Service-role only (no anon/authenticated policy)",
        "preview": None, "restricted_reason": "Contains credential material — count only.",
    },
    "conversations": {
        "category": "Chat", "timestamp": "created_at",
        "purpose": "Conversation containers (title + owner) for the AI chat.",
        "access": "User RLS (own rows)",
        "preview": None, "restricted_reason": "Private student content — count only.",
    },
    "messages": {
        "category": "Chat", "timestamp": "created_at",
        "purpose": "Individual chat messages.",
        "access": "User RLS (own rows); immutable",
        "preview": None, "restricted_reason": "Private student conversations — count only.",
    },
    "mood_events": {
        "category": "Wellbeing", "timestamp": "created_at",
        "purpose": "Mood signals from chat and check-ins.",
        "access": "User RLS (own rows)",
        "preview": None, "restricted_reason": "Sensitive wellbeing data — count only (aggregates live on the Dashboard).",
    },
    "wellness_activity_logs": {
        "category": "Wellbeing", "timestamp": "completed_at",
        "purpose": "Completed wellness activities (breathing, grounding, etc.).",
        "access": "User RLS (own rows)",
        "preview": ["activity_key", "completed_at"],
    },
    "feedback": {
        "category": "Feedback", "timestamp": "created_at",
        "purpose": "Student ratings and comments.",
        "access": "User RLS (own rows) + service-role for admin summary",
        "preview": ["rating", "created_at"],
        "restricted_reason": "Comment text is shown on the Feedback tab, not here.",
    },
    "safety_events": {
        "category": "Safety", "timestamp": "created_at",
        "purpose": "Which deterministic safety rule fired (category + crisis/block). No message content.",
        "access": "Service-role only",
        "preview": ["category", "action", "created_at"],
    },
    "audit_logs": {
        "category": "Security", "timestamp": "created_at",
        "purpose": "Auth/admin security event trail.",
        "access": "Service-role only",
        "preview": ["actor_type", "action", "created_at"],
    },
}

DB_PREVIEW_PAGE_SIZE_MAX = 50


def _classify_db_error(exc: Exception) -> str:
    text = str(exc).lower()
    if "42501" in text or "permission denied" in text or "not allowed" in text:
        return "denied"
    if ("pgrst205" in text or "42p01" in text or "does not exist" in text
            or "could not find the table" in text):
        return "missing"
    return "error"


def get_database_overview(admin: AdminUser) -> dict:
    """Per-table row count, newest-write timestamp and status for every
    table in DB_TABLE_REGISTRY. Never raises for a single bad table."""
    _require_admin(admin)
    client = get_admin_client()
    tables = []
    for name, meta in DB_TABLE_REGISTRY.items():
        row = {
            "table": name, "category": meta["category"], "purpose": meta["purpose"],
            "access": meta["access"], "previewable": meta["preview"] is not None,
            "restricted_reason": meta.get("restricted_reason"),
            "rows": None, "latest": None, "status": "ok",
        }
        try:
            result = client.table(name).select("id", count="exact").limit(1).execute()
            row["rows"] = result.count
            if result.count:
                col = meta["timestamp"]
                newest = client.table(name).select(col).order(col, desc=True).limit(1).execute().data or []
                row["latest"] = newest[0].get(col) if newest else None
        except Exception as exc:  # noqa: BLE001
            row["status"] = _classify_db_error(exc)
        tables.append(row)
    ok = [t for t in tables if t["status"] == "ok"]
    return {
        "tables": tables,
        "table_count": len(tables),
        "reachable": len(ok),
        "total_rows": sum(t["rows"] or 0 for t in ok),
        "problems": [t["table"] for t in tables if t["status"] != "ok"],
    }


def get_table_preview(admin: AdminUser, table: str, page: int = 1, page_size: int = 25) -> dict:
    """Newest-first, read-only page of SAFE columns for an allow-listed table.
    Raises ValueError for any table that is not previewable."""
    _require_admin(admin)
    meta = DB_TABLE_REGISTRY.get(table)
    if meta is None or not meta["preview"]:
        raise ValueError("This table is not available for record preview.")
    page = max(1, int(page))
    page_size = max(1, min(int(page_size), DB_PREVIEW_PAGE_SIZE_MAX))
    start = (page - 1) * page_size
    cols = meta["preview"]
    client = get_admin_client()
    result = (
        client.table(table).select(", ".join(cols), count="exact")
        .order(meta["timestamp"], desc=True).range(start, start + page_size - 1).execute()
    )
    return {"table": table, "columns": cols, "rows": result.data or [],
            "total": result.count, "page": page, "page_size": page_size}

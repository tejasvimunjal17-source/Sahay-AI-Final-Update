"""
backend/safety_log.py
------------------------
PHASE 7 IMPLEMENTATION.

The ONLY writer of the safety_events table, mirroring
backend/audit_log.py's existing pattern for audit_logs. Called from
chatbot/response_generator.py after a crisis or block outcome — never
for "allow" (there's nothing to monitor about a normal turn).

SENSITIVE DATA RULE (enforced by what this function accepts, not just by
convention): log_safety_event() has no parameter for message content, AI
replies, or any free text — only a user_id, a category string (one of
chatbot/safety.py's existing category names), and an action
('crisis'/'block'). There is no way to call this function with
conversation content even by mistake, because the function signature
doesn't accept it.
"""

from __future__ import annotations

from backend.logging_config import get_logger
from backend.supabase_admin_client import get_admin_client, SupabaseAdminNotConfiguredError

logger = get_logger(__name__)

VALID_ACTIONS = ("crisis", "block")


def log_safety_event(user_id: str | None, category: str, action: str) -> None:
    """Best-effort write — NEVER raises into the caller. A logging
    failure must not block or alter the chat turn the user is having;
    the safety response itself (chatbot/safety.py's deterministic text)
    has already been decided and shown regardless of whether this
    succeeds."""
    if action not in VALID_ACTIONS:
        logger.warning("log_safety_event: invalid action %r, skipping write", action)
        return
    try:
        client = get_admin_client()
        client.table("safety_events").insert({
            "user_id": user_id,
            "category": category,
            "action": action,
        }).execute()
    except SupabaseAdminNotConfiguredError:
        logger.info("Safety event logging skipped (service-role client not configured): %s/%s", category, action)
    except Exception:  # noqa: BLE001 - safety event logging must never break the chat turn
        logger.exception("Failed to write safety event: %s/%s", category, action)

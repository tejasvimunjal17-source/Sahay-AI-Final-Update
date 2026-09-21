"""
backend/admin_auth.py
------------------------
PHASE 7 IMPLEMENTATION.

Admin authentication — completely independent from backend/auth.py's
Supabase Auth flow for students. Admins are NOT Supabase Auth users:
their credentials live in the service-role-only admin_users table
(011_admin_users.sql), checked with bcrypt, never through
sign_in_with_password or any student-facing code path.

SESSION MODEL: st.session_state["sahay_admin_session"] holds
{"admin_id", "email"} once verified — a separate key from
"sahay_supabase_session" (students), so a student session and an admin
session can never be confused with each other, and clearing one never
accidentally affects the other.

bcrypt is imported lazily inside functions, matching this codebase's
established pattern (see backend/openrouter_client.py, exports/pdf.py)
so this module stays importable even in an environment without bcrypt
installed. NOT LIVE-TESTED: bcrypt could not be installed in this
sandbox (no network access — same constraint as every prior phase's
optional-dependency installs). See PHASE7_IMPLEMENTATION_REPORT.md.

NO PUBLIC SIGN-UP PATH EXISTS. The first admin account is created via a
documented manual procedure (see README.md) — never auto-provisioned,
never hardcoded here or anywhere else in this codebase.
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from backend.logging_config import get_logger
from backend.supabase_admin_client import get_admin_client, SupabaseAdminNotConfiguredError

logger = get_logger(__name__)

ADMIN_SESSION_KEY = "sahay_admin_session"


class AdminAuthError(RuntimeError):
    """User-safe error message — never contains a password, hash, or raw exception."""


@dataclass(frozen=True)
class AdminUser:
    id: str
    email: str
    display_name: str | None


def admin_sign_in(email: str, password: str) -> AdminUser:
    """Verifies email+password against admin_users via bcrypt, using the
    service-role client (the ONLY legitimate reason to read this table —
    see 011_admin_users.sql's RLS comment). Raises AdminAuthError with a
    generic message on any failure — deliberately does not distinguish
    "no such admin" from "wrong password" in the message shown to the
    caller, to avoid leaking which emails are registered admins."""
    try:
        import bcrypt
    except ImportError as exc:
        raise AdminAuthError(
            "Admin sign-in isn't available right now — a required library isn't installed."
        ) from exc

    try:
        client = get_admin_client()
        resp = client.table("admin_users").select("*").eq("email", email).eq("is_active", True).execute()
    except SupabaseAdminNotConfiguredError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("admin_sign_in: lookup failed")
        raise AdminAuthError("Couldn't sign in right now. Please try again.") from exc

    rows = resp.data or []
    if not rows:
        logger.info("Admin sign-in attempt for unknown/inactive email")
        raise AdminAuthError("Incorrect email or password.")

    row = rows[0]
    try:
        password_matches = bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - malformed hash, etc. — never crash, just deny
        logger.exception("admin_sign_in: bcrypt check failed")
        raise AdminAuthError("Incorrect email or password.") from exc

    if not password_matches:
        logger.info("Admin sign-in attempt with incorrect password")
        raise AdminAuthError("Incorrect email or password.")

    admin = AdminUser(id=row["id"], email=row["email"], display_name=row.get("display_name"))
    st.session_state[ADMIN_SESSION_KEY] = {"admin_id": admin.id, "email": admin.email}

    try:
        client.table("admin_users").update({"last_login_at": "now()"}).eq("id", admin.id).execute()
    except Exception:  # noqa: BLE001 - last-login tracking must never break sign-in
        logger.warning("admin_sign_in: failed to update last_login_at")

    return admin


def get_current_admin() -> AdminUser | None:
    """The single source of truth for 'is this a real, verified admin
    session' — re-validates against admin_users on every call rather
    than trusting the cached session_state dict alone, so a deactivated
    admin (is_active=False) loses access immediately, not just at next
    login."""
    session = st.session_state.get(ADMIN_SESSION_KEY)
    if not session:
        return None
    try:
        client = get_admin_client()
        resp = client.table("admin_users").select("*").eq("id", session["admin_id"]).eq("is_active", True).execute()
    except SupabaseAdminNotConfiguredError:
        return None
    except Exception:  # noqa: BLE001
        logger.exception("get_current_admin: re-validation failed")
        return None

    rows = resp.data or []
    if not rows:
        st.session_state.pop(ADMIN_SESSION_KEY, None)
        return None
    row = rows[0]
    return AdminUser(id=row["id"], email=row["email"], display_name=row.get("display_name"))


def admin_sign_out() -> None:
    st.session_state.pop(ADMIN_SESSION_KEY, None)

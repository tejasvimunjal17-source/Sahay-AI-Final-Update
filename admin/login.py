"""
admin/login.py
-----------------
PHASE 7 IMPLEMENTATION.

Admin login form. Reachable ONLY via the ?admin=1 entry point handled in
streamlit_app.py — never linked from the student sidebar, never
reachable from a normal student session. Uses backend.admin_auth
exclusively; never touches backend.auth (student Supabase Auth) or
st.session_state["sahay_supabase_session"].

ADMIN UI UPGRADE: presentation only. The form, its widget keys, the
admin_auth.admin_sign_in() call, and every message shown for a missing
field / rejected credentials / unavailable service are unchanged — only
the hero header, card styling, full-width sign-in button and a "Back to
Sahay AI" link were added (styles live in admin/theme.py).
"""

from __future__ import annotations

import streamlit as st

from admin.theme import inject_admin_css
from components.theme import hide_sidebar_css


def render() -> None:
    # Collapse any sidebar DOM left over from an authenticated admin
    # session (same rendering-artifact guard the student landing page
    # uses after a logout) — the login page never has a sidebar.
    hide_sidebar_css()
    inject_admin_css(login=True)

    st.markdown(
        "<div class='sahay-admin-hero'>"
        "<span class='sahay-admin-badge'>Admin Panel</span>"
        "<div class='sahay-admin-hero-title'>"
        "<span>🛡️</span><span class='sahay-admin-grad'>Sahay AI — Admin Login</span>"
        "</div>"
        "<div class='sahay-admin-hero-sub'>"
        "Administrator sign-in. This area is separate from student accounts."
        "</div></div>",
        unsafe_allow_html=True,
    )

    with st.form("admin_login_form", border=True):
        email = st.text_input("Admin email", key="admin_login_email")
        password = st.text_input("Password", type="password", key="admin_login_password")
        submitted = st.form_submit_button("🔐 Sign in", type="primary", use_container_width=True)

    # Messages render here (directly under the form), while the "Back"
    # link below is always drawn regardless of how submission goes.
    feedback = st.container()

    st.markdown(
        "<hr class='sahay-admin-divider'/>"
        "<a href='?' class='sahay-admin-back' target='_self'>← Back to Sahay AI</a>",
        unsafe_allow_html=True,
    )

    if submitted:
        with feedback:
            if not email or not password:
                st.warning("Please enter both an email and password.")
            else:
                from backend import admin_auth
                try:
                    admin_auth.admin_sign_in(email, password)
                    st.rerun()
                except admin_auth.AdminAuthError as exc:
                    st.error(str(exc))
                except Exception as exc:  # noqa: BLE001 - e.g. service-role client not configured
                    st.error("Admin sign-in isn't available right now. Please try again later.")
                    st.caption(f"Technical detail (dev preview only): {exc}")

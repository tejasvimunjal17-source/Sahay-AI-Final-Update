"""
admin/login.py
-----------------
PHASE 7 IMPLEMENTATION.

Admin login form. Reachable ONLY via the ?admin=1 entry point handled in
streamlit_app.py — never linked from the student sidebar, never
reachable from a normal student session. Uses backend.admin_auth
exclusively; never touches backend.auth (student Supabase Auth) or
st.session_state["sahay_supabase_session"].
"""

from __future__ import annotations

import streamlit as st

from components.theme import sahay_icon_html


def render() -> None:
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:6px;'>"
        f"{sahay_icon_html(28)}<span style='font-weight:700;font-size:18px;'>Sahay AI — Admin</span></div>",
        unsafe_allow_html=True,
    )
    st.caption("Administrator sign-in. This area is separate from student accounts.")

    with st.form("admin_login_form", border=True):
        email = st.text_input("Admin email", key="admin_login_email")
        password = st.text_input("Password", type="password", key="admin_login_password")
        submitted = st.form_submit_button("Sign in", type="primary")

    if submitted:
        if not email or not password:
            st.warning("Please enter both an email and password.")
            return
        from backend import admin_auth
        try:
            admin_auth.admin_sign_in(email, password)
            st.rerun()
        except admin_auth.AdminAuthError as exc:
            st.error(str(exc))
        except Exception as exc:  # noqa: BLE001 - e.g. service-role client not configured
            st.error("Admin sign-in isn't available right now. Please try again later.")
            st.caption(f"Technical detail (dev preview only): {exc}")

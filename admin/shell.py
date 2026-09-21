"""
admin/shell.py
-----------------
PHASE 7 IMPLEMENTATION.

The authenticated admin app shell — nav across the admin sections +
logout. Only ever rendered after admin/login.py's flow has produced a
verified AdminUser (see streamlit_app.py's admin gate) — this module
itself does not re-check auth, matching the pattern where
streamlit_app.py's main() is the single place authorization is decided.
"""

from __future__ import annotations

import streamlit as st

from components.theme import sahay_icon_html
from backend.admin_auth import AdminUser

SECTIONS = ["Dashboard", "Users", "Feedback", "Safety Events", "System"]


def render(admin: AdminUser) -> None:
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:10px;'>"
        f"{sahay_icon_html(26)}<span style='font-weight:700;font-size:16px;'>Sahay AI — Admin</span>"
        f"<span style='color:#6B7280;font-size:12px;'>· {admin.email}</span></div>",
        unsafe_allow_html=True,
    )

    nav_col, logout_col = st.columns([5, 1])
    with nav_col:
        st.session_state.setdefault("admin_active_section", "Dashboard")
        chosen = st.radio("Section", SECTIONS, horizontal=True, label_visibility="collapsed",
                           index=SECTIONS.index(st.session_state["admin_active_section"]))
        st.session_state["admin_active_section"] = chosen
    with logout_col:
        if st.button("Log out", key="admin_logout"):
            from backend.admin_auth import admin_sign_out
            admin_sign_out()
            st.rerun()

    st.markdown("---")

    from admin import views
    section = st.session_state["admin_active_section"]
    if section == "Dashboard":
        views.render_dashboard(admin)
    elif section == "Users":
        views.render_users(admin)
    elif section == "Feedback":
        views.render_feedback(admin)
    elif section == "Safety Events":
        views.render_safety(admin)
    elif section == "System":
        views.render_system(admin)

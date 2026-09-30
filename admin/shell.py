"""
admin/shell.py
-----------------
PHASE 7 IMPLEMENTATION.

The authenticated admin app shell — nav across the admin sections +
logout. Only ever rendered after admin/login.py's flow has produced a
verified AdminUser (see streamlit_app.py's admin gate) — this module
itself does not re-check auth, matching the pattern where
streamlit_app.py's main() is the single place authorization is decided.

ADMIN UI UPGRADE: the horizontal radio nav is replaced by a dedicated
ADMIN sidebar drawer (own widget keys, own `admin_sidebar_open` state,
styles in admin/theme.py — the student sidebar in components/sidebar.py
is not touched). `admin_active_section` is the same session key as
before. The five sections that already had views (Dashboard, Users,
Feedback, Safety Events, System) still call the same admin/views.py
functions, unchanged. Database now has a read-only view
(views.render_database). The remaining tabs (Announcements,
Notifications, Analytics, Export) have NO backend in this codebase, so
they show an honest "not available yet" panel — no fake data, no fake
features. Announcements/Notifications are blocked on a schema that has
not been created or approved (they need new tables).
"""

from __future__ import annotations

import html

import streamlit as st

from admin.theme import (
    BACKDROP_BOX_KEY,
    BACKDROP_BTN_KEY,
    TOGGLE_BOX_KEY,
    TOGGLE_BTN_KEY,
    inject_admin_css,
    inject_admin_drawer_css,
)
from backend.admin_auth import AdminUser

# (group label, [(section label, icon), ...]) — labels are the exact
# Admin Panel tab names; grouping is presentation only.
NAV_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    ("Admin", [("Dashboard", "📊")]),
    ("Data", [("Database", "🗄️"), ("Users", "👥")]),
    ("Safety", [("Safety Events", "🚨")]),
    ("Management", [
        ("System", "⚙️"),
        ("Feedback", "💬"),
        ("Announcements", "📣"),
        ("Notifications", "🔔"),
    ]),
    ("Insights", [("Analytics", "📈"), ("Export", "⬇️")]),
]

SECTIONS = [label for _, items in NAV_GROUPS for label, _ in items]

# Tabs with no implementation behind them in this codebase. Text states
# only what is true of this build.
_NOT_AVAILABLE: dict[str, str] = {
    "Announcements": (
        "Announcements aren't available yet: saving and publishing them needs a new database table "
        "that hasn't been created. Nothing is stored or sent from this tab."
    ),
    "Notifications": (
        "Notifications aren't available yet: storing them and tracking read/unread state needs new "
        "database tables that haven't been created. Nothing is stored or sent from this tab."
    ),
    "Export": "Admin data export isn't implemented in this Sahay AI build yet.",
}


def _slug(label: str) -> str:
    return label.lower().replace(" ", "_")


def _render_drawer_shell() -> None:
    """Fixed 🛡️ toggle + mobile tap-to-close backdrop + drawer CSS.
    Same interaction pattern as the student sidebar, admin-only keys."""
    is_open = st.session_state["admin_sidebar_open"]

    with st.container(key=TOGGLE_BOX_KEY):
        toggle_clicked = st.button("🛡️", key=TOGGLE_BTN_KEY, help="Open / close navigation")

    with st.container(key=BACKDROP_BOX_KEY):
        backdrop_clicked = st.button("", key=BACKDROP_BTN_KEY, help="Close navigation")

    if toggle_clicked or (backdrop_clicked and is_open):
        st.session_state["admin_sidebar_open"] = not st.session_state["admin_sidebar_open"]
        is_open = st.session_state["admin_sidebar_open"]

    inject_admin_drawer_css(is_open)


def _render_sidebar(admin: AdminUser, active: str) -> None:
    with st.sidebar:
        st.markdown(
            "<div style='display:flex;align-items:center;gap:8px;padding:4px 0 2px 0;'>"
            "<span style='font-size:22px;line-height:1;'>🛡️</span>"
            "<span class='sahay-display' style='font-size:19px;font-weight:700;'>Sahay AI — Admin</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        for group_label, items in NAV_GROUPS:
            st.markdown(
                f"<div class='sahay-sidebar-group-label'>{group_label}</div>",
                unsafe_allow_html=True,
            )
            for label, icon in items:
                if st.button(
                    f"{icon}  {label}",
                    key=f"admin_nav_{_slug(label)}",
                    use_container_width=True,
                    type="primary" if label == active else "secondary",
                ):
                    st.session_state["admin_active_section"] = label
                    st.rerun()

        who = html.escape(admin.display_name or admin.email)
        st.markdown("<div class='sahay-sidebar-profile'></div>", unsafe_allow_html=True)
        st.markdown(
            f"**{who}**  \n"
            "<span style='font-size:12px;color:#6B7280;'>Signed in as administrator</span>",
            unsafe_allow_html=True,
        )
        if st.button("Log out", key="admin_logout", use_container_width=True):
            from backend.admin_auth import admin_sign_out
            admin_sign_out()
            st.rerun()


def _render_not_available(section: str) -> None:
    st.markdown(f"### {section}")
    if section == "Analytics":
        st.markdown(
            "<div class='sahay-card'><div class='sahay-card-muted-label'>Not a separate page yet</div>"
            "<div style='font-size:15px;'>The usage, mood, language, and wellness-activity charts "
            "currently live on the Dashboard tab.</div></div>",
            unsafe_allow_html=True,
        )
        if st.button("Open Dashboard", key="admin_analytics_open_dashboard"):
            st.session_state["admin_active_section"] = "Dashboard"
            st.rerun()
        return
    st.markdown(
        "<div class='sahay-card'><div class='sahay-card-muted-label'>Not available yet</div>"
        f"<div style='font-size:15px;'>{_NOT_AVAILABLE[section]}</div></div>",
        unsafe_allow_html=True,
    )


def render(admin: AdminUser) -> None:
    st.session_state.setdefault("admin_active_section", "Dashboard")
    st.session_state.setdefault("admin_sidebar_open", True)
    if st.session_state["admin_active_section"] not in SECTIONS:
        st.session_state["admin_active_section"] = "Dashboard"

    inject_admin_css()
    _render_drawer_shell()

    section = st.session_state["admin_active_section"]
    _render_sidebar(admin, section)

    st.markdown(
        "<div class='sahay-admin-topline'>"
        "<span class='sahay-admin-badge'>🛡️ Admin Panel</span>"
        f"<span class='sahay-admin-who'>{html.escape(admin.email)}</span></div>",
        unsafe_allow_html=True,
    )

    from admin import views
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
    elif section == "Database":
        views.render_database(admin)
    else:
        _render_not_available(section)

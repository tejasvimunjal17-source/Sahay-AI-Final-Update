"""
components/topbar.py
---------------------
Top utility bar + page header for the authenticated Sahay AI dashboard.

PHASE 4: restyled into an elevated "page header" card — date/utility row
+ large page title — sitting at the top of the main content area,
in normal document flow (not `position: fixed`, unlike LearnMate's own
topnav — see the PHASE 4 note this module carried before this change
for why that was a deliberate choice, still true here).

USER-DASHBOARD UPGRADE (this task): the previous 🔔/👤 were static,
non-interactive placeholder glyphs ("No auth or notification data is
real yet"). This bar is now rendered with real Streamlit widgets inside
`st.container(key="sahay_topbar")` (same real-DOM-ancestor technique
components/landing.py's hero and components/chatbot_launcher.py's
launcher already use — see either docstring) so it can hold three real,
data-backed controls, in a persistent position at the very top of
EVERY authenticated page (this function is called once per page render
from streamlit_app.py's main()) — matching how the LearnMate AI
reference keeps its streak/profile/notification affordances
persistently visible across every page, not confined to one screen.
Left-to-right order in this bar: streak pill (top-left), page title,
then the notification bell and profile chip pushed to the right:

1. STREAK PILL — "🔥 N", popover reveals the same 7-day strip as
   components/streak_widget.py, backed by backend/streak.py's real,
   already-existing streak computation (unchanged; reused exactly as
   before, just relocated — see that module for the no-fake-data logic).
   PLACEMENT: explicitly confirmed as TOP-LEFT — the written requirement
   is authoritative over the LearnMate screenshots' top-right placement
   (screenshots are visual/UX reference only, per this task's own
   instructions). Rendered as the FIRST (leftmost) element of this bar,
   to the left of the page title, on every authenticated page.

2. NOTIFICATION BELL — "🔔", popover. HONEST SHELL, NOT FAKE DATA: this
   codebase has no notification/announcement data source anywhere (see
   admin/shell.py's own `_NOT_AVAILABLE["Notifications"]` string —
   Announcements/Notifications have no backend in this build). Per this
   task's explicit instruction to STOP rather than invent a table, this
   renders a real, always-present bell that honestly reports "No
   notifications yet" and explains why, exactly mirroring the wording
   pattern admin/shell.py already uses for its own unimplemented tabs.
   No table was added; see the task's final report for what a real
   version would need.

3. PROFILE CHIP — "👤", popover showing the actual signed-in user's
   real display name (from the `profiles` row profile.py already reads/
   writes — backend.auth.get_profile) or email local-part fallback, or
   an honest "Not signed in" state in Demo Mode. Never hardcoded.

All three are read-only, best-effort (wrapped so a Supabase hiccup
degrades to an empty/neutral state rather than crashing the page — the
topbar is chrome, not critical navigation) and never touch
authentication, RLS, or session-state contracts beyond reading them.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from components.theme import COLORS
from components.streak_widget import render_streak_popover_content


def _current_user():
    """Best-effort: the signed-in AuthUser, or None in Demo Mode / on
    any auth hiccup (the topbar must never crash a page)."""
    if not st.session_state.get("sahay_supabase_session"):
        return None
    try:
        from backend import auth
        return auth.get_current_user()
    except Exception:  # noqa: BLE001
        return None


def _profile_display_name(user) -> str | None:
    """Real display name from the user's own `profiles` row (the same
    source pages/profile.py reads/edits), falling back to their email's
    local part, or None if neither is available. Never hardcoded, never
    fabricated."""
    if user is None:
        return None
    try:
        from backend import auth
        profile = auth.get_profile(user)
    except Exception:  # noqa: BLE001
        profile = None
    name = (profile or {}).get("display_name")
    if name:
        return name
    if user.email:
        return user.email.split("@", 1)[0]
    return None


def _user_streak(user):
    """Reuses backend.streak.get_user_streak() exactly as before —
    real activity only, no new logic. None for a signed-out viewer."""
    if user is None:
        return None
    try:
        from backend import conversations as conv_db
        from backend.streak import get_user_streak
        return get_user_streak(user, conv_db)
    except Exception:  # noqa: BLE001
        return None


def _render_streak_pill(streak) -> None:
    label = f"🔥 {streak.current_streak}" if streak is not None else "🔥 –"
    with st.popover(label, use_container_width=True):
        render_streak_popover_content(streak)


def _render_notification_bell() -> None:
    with st.popover("🔔", use_container_width=True):
        st.markdown("**Notifications**")
        st.caption(
            "No notifications yet. Live announcements from Sahay AI aren't enabled "
            "in this build yet — this panel is ready for them."
        )


def _render_profile_chip(user, display_name: str | None) -> None:
    icon_label = "👤" if not display_name else f"👤 {display_name.split()[0]}"
    with st.popover(icon_label, use_container_width=True):
        if user is None:
            st.markdown("**Not signed in**")
            st.caption("You're browsing Sahay AI in Demo Mode.")
        else:
            st.markdown(f"**{display_name or 'Signed in'}**")
            st.caption(user.email or "")
            st.caption("Manage your name and language in Profile · Sign out from the sidebar.")


_TOPBAR_CSS = """
<style>
div[class*="st-key-sahay_topbar"] {
    border-radius: var(--sahay-radius, 18px);
    border: 1px solid var(--sahay-border, rgba(20,24,33,0.08));
    box-shadow: var(--sahay-shadow, 0 4px 20px rgba(20,24,33,0.06));
    padding: 10px 16px 14px 16px;
    margin-bottom: 20px;
}
div[class*="st-key-sahay_topbar"] div[data-testid="stPopoverButton"] > button,
div[class*="st-key-sahay_topbar"] button[kind="secondary"] {
    border-radius: 999px !important;
    padding: 2px 12px !important;
    font-size: 13px !important;
    min-height: 0 !important;
}
</style>
"""


def render_topbar(page_title: str) -> None:
    user = _current_user()
    display_name = _profile_display_name(user)
    streak = _user_streak(user)

    dark = st.session_state.get("sahay_dark_mode", True)
    muted = COLORS["muted_dark"] if dark else COLORS["muted_light"]

    with st.container(key="sahay_topbar"):
        # Streak pill is the FIRST (leftmost) column — top-left placement,
        # confirmed authoritative over the LearnMate screenshots' top-right
        # example (see module docstring). Title sits to its right; the
        # bell/profile cluster is pushed to the far right by the spacer.
        streak_col, title_col, spacer_col, bell_col, profile_col = st.columns(
            [0.9, 3.6, 1.0, 0.7, 1.5]
        )

        with streak_col:
            st.markdown("<div style='padding-top:2px;'></div>", unsafe_allow_html=True)
            _render_streak_pill(streak)

        with title_col:
            st.markdown(
                f"""
                <div style="padding-top:6px;">
                    <div style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:22px;">
                        {page_title}
                    </div>
                    <div style="color:{muted};font-size:12.5px;margin-top:2px;">
                        {datetime.now().strftime('%A, %d %B %Y')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with bell_col:
            st.markdown("<div style='padding-top:2px;'></div>", unsafe_allow_html=True)
            _render_notification_bell()
        with profile_col:
            st.markdown("<div style='padding-top:2px;'></div>", unsafe_allow_html=True)
            _render_profile_chip(user, display_name)

    st.markdown(_TOPBAR_CSS, unsafe_allow_html=True)

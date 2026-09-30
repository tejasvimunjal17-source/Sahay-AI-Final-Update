"""
components/topbar.py
---------------------
STREAK UPDATE: the top-right streak is now the LearnMate-style "🔥 N" pill
that opens a "Learning Streak" dialog (components/streak_widget.py:
render_streak_control) instead of a popover. Same single global position,
same real data (backend/streak.py, unchanged).

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

LAYOUT UPDATE (My Profile task): the streak pill now sits at the
TOP-RIGHT (per the final layout spec), opening the same popover on every
page. The bell and profile chip were removed from this bar — the
notification panel and the user's name/email now live in the sidebar
(components/sidebar.py), so identity is not repeated beside every page
title. Streak data/logic (backend/streak.py) is untouched.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from components.theme import COLORS
from components.streak_widget import render_streak_control


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
/* Mobile: keep the page title and the top-right streak on ONE row
   instead of letting Streamlit stack the columns. */
@media (max-width: 640px) {
    div[class*="st-key-sahay_topbar"] div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        gap: 0.5rem !important;
    }
    div[class*="st-key-sahay_topbar"] div[data-testid="stColumn"],
    div[class*="st-key-sahay_topbar"] div[data-testid="column"] {
        min-width: 0 !important;
        width: auto !important;
    }
    div[class*="st-key-sahay_topbar"] div[data-testid="stColumn"]:first-child,
    div[class*="st-key-sahay_topbar"] div[data-testid="column"]:first-child {
        flex: 1 1 0 !important;
    }
    div[class*="st-key-sahay_topbar"] div[data-testid="stColumn"]:last-child,
    div[class*="st-key-sahay_topbar"] div[data-testid="column"]:last-child {
        flex: 0 0 auto !important;
    }
}
</style>
"""


def render_topbar(page_title: str) -> None:
    user = _current_user()
    streak = _user_streak(user)

    dark = st.session_state.get("sahay_dark_mode", True)
    muted = COLORS["muted_dark"] if dark else COLORS["muted_light"]

    with st.container(key="sahay_topbar"):
        # Page title on the left, the global streak trigger at the far
        # right. The same popover shows on every page. User identity and
        # notifications live in the sidebar, not here.
        title_col, streak_col = st.columns([4, 1.2])

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

        with streak_col:
            st.markdown("<div style='padding-top:2px;'></div>", unsafe_allow_html=True)
            render_streak_control(streak)

    st.markdown(_TOPBAR_CSS, unsafe_allow_html=True)

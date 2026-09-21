"""pages/settings.py — PHASE 1: dark mode toggle. PHASE 7: adds a minimal
feedback submission form (rating + optional message), authenticated
users only — Demo Mode shows an explanatory message instead, since
feedback requires a real account to be meaningfully attributable and
there's nothing to persist it to in Demo Mode.

PHASE 6F: header swapped to render_page_header (no description added —
none existed before). The one existing "##### Send feedback" heading
became a render_section_header call, title only (no description — none
existed). The dark-mode toggle line is UNTOUCHED, character-for-
character — this is the single source of truth for
`st.session_state["sahay_dark_mode"]`, read by components/theme.py's
inject_css() and components/chatbot_launcher.py's
_fixed_chatbot_css() app-wide, so it was left exactly as it was: same
`st.toggle("Dark mode", value=...)` call (no widget key, same as
before), same comparison-then-write-then-rerun logic, same
`sahay_dark_mode` key, nothing added, nothing renamed. The notification
selectbox, the auth check, the feedback rating/message widgets and
their keys, and the `conv_db.submit_feedback(...)` call are all
byte-identical to before."""

from __future__ import annotations

import streamlit as st

from components.page_components.page_header import render_page_header
from components.page_components.section_header import render_section_header
from backend import auth


def render() -> None:
    render_page_header("Settings")
    dark = st.toggle("Dark mode", value=st.session_state.get("sahay_dark_mode", False))
    if dark != st.session_state.get("sahay_dark_mode", False):
        st.session_state["sahay_dark_mode"] = dark
        st.rerun()
    st.selectbox("Notification preferences", ["Email", "None"], disabled=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    render_section_header("Send feedback")

    user = auth.get_current_user() if st.session_state.get("sahay_supabase_session") else None
    if user is None:
        st.info("Sign in to send feedback about Sahay AI.")
        return

    rating = st.select_slider("How's your experience been?", options=[1, 2, 3, 4, 5], value=4, key="feedback_rating")
    message = st.text_area("Anything you'd like to share? (optional)", key="feedback_message")

    if st.button("Send feedback", key="settings_send_feedback"):
        from backend import conversations as conv_db
        try:
            conv_db.submit_feedback(user, rating=rating, message=message or None)
            st.success("Thank you — your feedback has been sent.")
        except Exception as exc:  # noqa: BLE001
            st.error("Couldn't send feedback right now. Please try again.")
            st.caption(f"Technical detail (dev preview only): {exc}")

"""pages/overview.py — Home dashboard.

PHASE 1 VALIDATION UPDATE: replaced empty "—" metric placeholders with
clearly-labeled sample/demo figures so the dashboard reads as an
interactive product preview rather than a grid of blank boxes. Every
card is explicitly captioned "Demo data" — nothing here is a real user's
data, and no health/mood statistic is implied to be clinically meaningful.

PHASE 6D: header + its existing intro sentence swapped from
`st.markdown("### ...")` + a separate `st.write(...)` into a single
components.page_components.render_page_header call — the intro sentence
becomes the header's `description` argument verbatim (nothing reworded,
nothing invented). Everything below (safety_note, the demo-data caption,
the 4 metric_card calls, the spacer, and the accent_card + its
sahay_page="companion" navigation) is byte-identical to before.

STREAK FEATURE (User Dashboard upgrade, explicitly requested): added a
single real-data streak card at the top-left, above the existing demo
metrics row. This is the ONLY change in this file — the 4 metric_card
calls, their "Demo data" captions, and the accent_card below remain
byte-identical and still show sample data as before (that scope was not
part of this task). For a signed-in user the streak is computed from
their own stored activity (backend/streak.py, reusing existing
conversations/mood_events/wellness_activity_logs reads — no new table,
no mock numbers). Demo Mode / signed-out shows an honest "sign in to
track" placeholder instead of a fabricated figure."""

from __future__ import annotations

import streamlit as st

from components.cards import metric_card, accent_card, safety_note
from components.page_components.page_header import render_page_header
from components.streak_widget import render_streak_widget


def _current_user_streak():
    """Returns backend.streak.StreakData for a real signed-in user, or
    None for Demo Mode / signed-out — never a fabricated value. Any
    fetch error is treated the same as "no user" rather than crashing
    the Home page (streak is a supplementary card, not core navigation)."""
    if not st.session_state.get("sahay_supabase_session"):
        return None
    try:
        from backend import auth
        user = auth.get_current_user()
        if user is None:
            return None
        from backend import conversations as conv_db
        from backend.streak import get_user_streak
        return get_user_streak(user, conv_db)
    except Exception:  # noqa: BLE001 - streak card degrades gracefully, rest of Home still renders
        return None


def render() -> None:
    render_page_header(
        "Good to see you.",
        description="This is a reflection space — not a medical assessment or diagnosis.",
    )
    safety_note(
        "Sahay is an AI wellness companion for student support and guidance. "
        "It is not a therapist, psychologist, psychiatrist, or doctor, and it "
        "does not replace professional care."
    )

    streak_col, _spacer_col = st.columns([1, 2])
    with streak_col:
        render_streak_widget(_current_user_streak())
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    st.caption("📊 Sample/demo data shown below — not connected to a real account yet.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Today's Check-in", "Not yet done", "Demo data · visit Mood Check-in")
    with c2:
        metric_card("Conversations", "3", "Demo data · this week")
    with c3:
        metric_card("Wellness Activities", "2", "Demo data · breathing, journaling")
    with c4:
        metric_card("Support Resources", "1", "Demo data · viewed this week")

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    clicked = accent_card(
        "Talk to Sahay",
        "Your companion is ready to listen whenever you are. Open the panel "
        "in the bottom-right corner, or head to the full Sahay Companion page.",
        cta_label="Open Sahay Companion",
    )
    if clicked:
        st.session_state["sahay_page"] = "companion"
        st.rerun()


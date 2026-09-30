"""
components/streak_widget.py
------------------------------
The single, global streak control for Sahay AI: a compact "🔥 N" pill in
the top-right of the page header (rendered by components/topbar.py) that
opens a "🔥 Learning Streak" dialog with the current streak and this
week's 7-day status row.

Adapted from LearnMate AI's streak_widget.py (control + @st.dialog popup
+ status-cell week row + motivational message). Only that behaviour was
ported. Sahay keeps its own data layer: everything shown here comes from
backend.streak.get_user_streak() (real per-user activity, no new table),
whose StreakData already uses the same day statuses LearnMate's popup
consumes (completed / today_active / today_inactive / missed / future).

Behaviour notes
- The dialog is opened directly from the pill's click run. There is no
  persistent "popup open" flag, so the X button, the Close button, and any
  navigation all close it and it can never re-open by itself on a rerun.
- Signed-out / Demo Mode: the pill shows "🔥 –" and the dialog says to sign
  in. No streak number is ever invented.
- Any failure while rendering the dialog is contained; it cannot take the
  page down.
"""

from __future__ import annotations

import streamlit as st

from backend.streak import StreakData
from components.theme import COLORS

_STATUS_LABELS = {
    "completed": "Completed",
    "today_active": "Today · done",
    "today_inactive": "Today",
    "missed": "Missed",
    "future": "Upcoming",
}


def _motivational_message(streak: int, active_today: bool) -> str:
    """Same tiers and copy as LearnMate's popup."""
    if streak == 0:
        return "Start your learning streak today!"
    if not active_today:
        return "Keep it going — do something today to extend your streak!"
    if streak < 3:
        return "Nice start — keep it going!"
    if streak < 7:
        return "Great consistency!"
    return "🔥 You're on fire! Amazing streak!"


def _streak_css(dark: bool) -> str:
    card = COLORS["card_dark"] if dark else COLORS["card_light"]
    text = COLORS["text_dark"] if dark else COLORS["text_light"]
    muted = COLORS["muted_dark"] if dark else COLORS["muted_light"]
    border = COLORS["border_dark"] if dark else COLORS["border_light"]
    grad = (
        f"linear-gradient(120deg, {COLORS['deep_blue']} 0%, "
        f"{COLORS['lavender']} 55%, {COLORS['soft_teal']} 100%)"
    )
    return f"""
<style>
/* --- top-right pill (scoped to this one button) --- */
div[class*="st-key-sahay_streak_toggle"] {{ display:flex; justify-content:flex-end; }}
div[class*="st-key-sahay_streak_toggle"] button {{
    background: {grad} !important;
    color: #fff !important;
    border: none !important;
    border-radius: 999px !important;
    padding: 2px 14px !important;
    min-height: 0 !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    width: auto !important;
}}
div[class*="st-key-sahay_streak_toggle"] button p {{ color: #fff !important; }}

/* --- dialog (only when it contains the streak hero) --- */
div[role="dialog"]:has(.sahay-streak-hero) {{
    background: {card};
    color: {text};
    max-width: min(440px, calc(100vw - 24px));
}}
.sahay-streak-hero {{ text-align:center; padding: 4px 0 0 0; }}
.sahay-streak-count {{
    font-size: 52px; font-weight: 700; line-height: 1.1;
    background: {grad}; -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent; color: {COLORS['deep_blue']};
}}
.sahay-streak-count-label {{ color: {muted}; font-size: 13px; font-weight: 600; margin-top: 2px; }}
.sahay-streak-divider {{ border: none; border-top: 1px solid {border}; margin: 16px 0; }}
.sahay-streak-week {{
    display:flex; justify-content:space-between; gap:4px;
    width:100%; box-sizing:border-box;
}}
.sahay-streak-day {{ flex:1 1 0; min-width:0; display:flex; flex-direction:column; align-items:center; gap:6px; }}
.sahay-streak-dot {{
    width: 28px; height: 28px; border-radius: 50%; box-sizing: border-box;
    border: 1.5px dashed {border}; background: transparent;
}}
.sahay-streak-day.is-completed .sahay-streak-dot,
.sahay-streak-day.is-today_active .sahay-streak-dot {{ background: {grad}; border: none; }}
.sahay-streak-day.is-today_inactive .sahay-streak-dot {{ border: 1.5px solid {COLORS['deep_blue']}; }}
.sahay-streak-day-label {{ font-size: 12px; color: {muted}; }}
.sahay-streak-day.is-today_active .sahay-streak-day-label,
.sahay-streak-day.is-today_inactive .sahay-streak-day-label {{ color: {text}; font-weight: 700; }}
@media (max-width: 640px) {{
    .sahay-streak-count {{ font-size: 44px; }}
    .sahay-streak-dot {{ width: 24px; height: 24px; }}
    .sahay-streak-day-label {{ font-size: 11px; }}
}}
</style>
"""


@st.dialog("🔥 Learning Streak")
def _render_streak_dialog(streak: StreakData | None, dark: bool) -> None:
    st.markdown(_streak_css(dark), unsafe_allow_html=True)

    if streak is None:
        st.markdown(
            '<div class="sahay-streak-hero"><div class="sahay-streak-count-label">'
            "Sign in to track your streak — it's based on your own activity only."
            "</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="sahay-streak-hero">
                <div class="sahay-streak-count">{int(streak.current_streak)}</div>
                <div class="sahay-streak-count-label">🔥 Current streak</div>
            </div>
            <hr class="sahay-streak-divider" />
            """,
            unsafe_allow_html=True,
        )
        cells = "".join(
            f'<div class="sahay-streak-day is-{d["status"]}" title="{_STATUS_LABELS.get(d["status"], "")}">'
            f'<div class="sahay-streak-dot"></div>'
            f'<div class="sahay-streak-day-label">{d["label"]}</div></div>'
            for d in streak.week_days
        )
        st.markdown(f'<div class="sahay-streak-week">{cells}</div>', unsafe_allow_html=True)
        st.caption(_motivational_message(streak.current_streak, streak.active_today))

    # st.rerun() closes the dialog; the X button closes it client-side.
    if st.button("Close", key="sahay_streak_close", use_container_width=True):
        st.rerun()


def render_streak_control(streak: StreakData | None) -> None:
    """Render THE global streak pill. Call exactly once per page render
    (components/topbar.py does). `streak` is the signed-in user's real
    StreakData, or None for Demo Mode / any load failure."""
    dark = st.session_state.get("sahay_dark_mode", True)
    st.markdown(_streak_css(dark), unsafe_allow_html=True)
    label = f"🔥 {streak.current_streak}" if streak is not None else "🔥 –"
    if st.button(label, key="sahay_streak_toggle"):
        try:
            _render_streak_dialog(streak, dark)
        except Exception:  # noqa: BLE001 - streak UI must never take the page down
            pass

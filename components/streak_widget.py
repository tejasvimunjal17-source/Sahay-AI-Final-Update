"""
components/streak_widget.py
------------------------------
Renders the User Dashboard streak indicator: a compact card at the
top-left of pages/overview.py showing the user's current streak plus a
7-day status strip, using Sahay AI's own `.sahay-card` styling
(components/theme.py) so it matches every other card on the dashboard.

Data comes exclusively from backend.streak.get_user_streak(), which
reads real, already-stored activity (see that module's docstring) - this
component never invents a number. Signed-out / Demo Mode renders an
honest "sign in to track" state instead of a fake streak.

The LearnMate AI screenshot supplied as a reference was used only to
match *placement and information hierarchy* (a small streak figure with
a weekly status row, top-left of the dashboard). No LearnMate markup,
CSS classes, copy, or colors are reused here - the classes below are
new (`sahay-streak-*`) and the colors come from components.theme.COLORS.
"""

from __future__ import annotations

import streamlit as st

from backend.streak import StreakData
from components.theme import COLORS

_STATUS_DOT = {
    "completed": "safe_green",
    "today_active": "safe_green",
    "today_inactive": "muted",
    "missed": "missed",
    "future": "future",
}


def _dot_color(status: str, dark: bool) -> str:
    if status in ("completed", "today_active"):
        return "#2FAE60"
    if status == "missed":
        return "#D97757" if not dark else "#C97355"
    if status == "future":
        return COLORS["border_dark"] if dark else COLORS["border_light"]
    return COLORS["muted_dark"] if dark else COLORS["muted_light"]


def render_streak_popover_content(streak: StreakData | None) -> None:
    """Compact content for the topbar's streak popover (components/topbar.py):
    the same real StreakData, same no-fake-data rule, just laid out for a
    small popover instead of a full-width card. Shares _dot_color() and
    the StreakData shape with render_streak_widget() below — no second
    streak implementation, only a second, smaller presentation of the
    same data."""
    dark = st.session_state.get("sahay_dark_mode", True)
    muted = COLORS["muted_dark"] if dark else COLORS["muted_light"]

    if streak is None:
        st.markdown("**Streak**")
        st.caption("Sign in to track your streak — it's based on your own activity only.")
        return

    if not streak.has_any_activity:
        caption = "Chat, check in, or try a relaxation activity today to start a streak."
    elif streak.current_streak == 0:
        caption = "Your streak reset — do something today to start a new one."
    elif streak.active_today:
        unit = "day" if streak.current_streak == 1 else "days"
        caption = f"{streak.current_streak} {unit} strong — keep it going!"
    else:
        caption = "Still counts today — be active before the day ends to extend it."

    st.markdown(f"**🔥 {streak.current_streak} current streak**")
    st.caption(caption)

    dots_html = "".join(
        f'<div class="sahay-streak-dot-col">'
        f'<span class="sahay-streak-dot" style="background:{_dot_color(d["status"], dark)};'
        f'{" outline:2px solid " + COLORS["deep_blue"] + ";" if d["is_today"] else ""}"></span>'
        f'<span class="sahay-streak-day-label" style="color:{muted};">{d["label"][0]}</span>'
        f"</div>"
        for d in streak.week_days
    )
    st.markdown(
        f'<div class="sahay-streak-week" style="margin-top:4px;">{dots_html}</div>'
        "<style>.sahay-streak-week{display:flex;gap:7px;}"
        ".sahay-streak-dot-col{display:flex;flex-direction:column;align-items:center;gap:3px;}"
        ".sahay-streak-dot{width:9px;height:9px;border-radius:50%;display:inline-block;}"
        ".sahay-streak-day-label{font-size:9px;}</style>",
        unsafe_allow_html=True,
    )


def render_streak_widget(streak: StreakData | None) -> None:
    """Renders the compact streak card.

    Args:
        streak: the user's real StreakData (backend.streak.get_user_streak),
            or None for a signed-out / Demo Mode viewer - in that case a
            clearly-labeled "sign in to track" placeholder is shown,
            never a fabricated streak number.
    """
    dark = st.session_state.get("sahay_dark_mode", False)
    muted = COLORS["muted_dark"] if dark else COLORS["muted_light"]

    if streak is None:
        st.markdown(
            f"""
            <div class="sahay-card sahay-streak-card">
                <div class="sahay-card-muted-label">🔥 Streak</div>
                <p class="sahay-card-metric" style="font-size:20px;margin:2px 0;">Sign in to track</p>
                <div class="sahay-card-caption" style="color:{muted};">
                    Your streak is based on your own activity — sign in for a real, private one.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if not streak.has_any_activity:
        caption = "Chat, check in, or try a relaxation activity today to start a streak."
    elif streak.current_streak == 0:
        caption = "Your streak reset — do something today to start a new one."
    elif streak.active_today:
        unit = "day" if streak.current_streak == 1 else "days"
        caption = f"{streak.current_streak} {unit} strong — keep it going!"
    else:
        caption = "Still counts today — be active before the day ends to extend it."

    dots_html = "".join(
        f'<div class="sahay-streak-dot-col">'
        f'<span class="sahay-streak-dot" style="background:{_dot_color(d["status"], dark)};'
        f'{" outline:2px solid " + COLORS["deep_blue"] + ";" if d["is_today"] else ""}"></span>'
        f'<span class="sahay-streak-day-label" style="color:{muted};">{d["label"][0]}</span>'
        f"</div>"
        for d in streak.week_days
    )

    st.markdown(
        f"""
        <div class="sahay-card sahay-streak-card">
            <div class="sahay-card-muted-label">🔥 Current streak</div>
            <p class="sahay-card-metric" style="font-size:28px;margin:2px 0;">{streak.current_streak}</p>
            <div class="sahay-card-caption" style="color:{muted};margin-bottom:10px;">{caption}</div>
            <div class="sahay-streak-week">{dots_html}</div>
        </div>
        <style>
        .sahay-streak-card {{ min-width: 168px; max-width: 240px; }}
        .sahay-streak-week {{ display:flex; gap:7px; }}
        .sahay-streak-dot-col {{ display:flex; flex-direction:column; align-items:center; gap:3px; }}
        .sahay-streak-dot {{ width:9px; height:9px; border-radius:50%; display:inline-block; }}
        .sahay-streak-day-label {{ font-size:9px; }}
        @media (max-width: 640px) {{
            .sahay-streak-card {{ min-width: 0; max-width: none; width: 100%; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

"""pages/mood_history.py — PHASE 5: adds mood-distribution and
stress/energy/sleep trend charts (via st.bar_chart/st.line_chart, no new
dependency — Streamlit bundles pandas), displays the new wellness scales
per record, and adds per-record deletion (backend.conversations.delete_mood_event)
alongside the existing "delete everything" control on the Privacy page.
Non-clinical framing preserved: charts describe self-reported trends only
("your recorded stress was higher this week"), never a clinical
interpretation ("your anxiety is getting worse").

PHASE 6E: header swapped to render_page_header (no description added —
none existed before). The three existing `st.markdown("##### ...")`
headings ("Mood distribution", "Self-reported trends", "Recent entries")
became render_section_header calls, using the paired existing caption
text as `description` where one exists (the first two) and no
description where none existed ("Recent entries").

The per-record entry row was deliberately left bespoke — NOT converted
to list_row, and delete was NOT wrapped in confirm_action. Two reasons,
found on re-inspection of the actual code before editing:
  1. Delete here is a single click with NO existing confirmation step —
     `st.button("🗑️", ...)` calls `conv_db.delete_mood_event(user,
     m["id"])` immediately. Wrapping it in confirm_action would ADD a
     confirm/cancel step that doesn't exist today — a behavior change,
     not a presentation change, which the Phase 6E scope explicitly
     forbids ("preserve the exact confirmation behavior" — the exact
     existing behavior is that there isn't one).
  2. Each row carries up to THREE separate text lines (the mood/date
     summary, an optional scales line, an optional note line) —
     list_row's API only accepts one `caption` string, so fitting this
     row into it would mean either dropping a line or merging visually
     distinct information into one block, which changes presentation
     in a way that loses the existing scales/note separation.
Both are reported here rather than silently forcing a mismatched
component. The row's rendering, the delete button's exact key
(f"delete_mood_{m['id']}"), and the delete-then-rerun call are all
byte-identical to before."""

from __future__ import annotations

from collections import Counter

import streamlit as st

from components.cards import empty_state, safety_note
from components.page_components.page_header import render_page_header
from components.page_components.section_header import render_section_header
from backend import auth
from chatbot.mood_analyzer import MOOD_EMOJI


def render() -> None:
    render_page_header("Mood History")
    safety_note(
        "A personal reflection log of approximate, self-reported and AI-generated "
        "wellness signals — not a clinical record or medical measurement."
    )

    user = auth.get_current_user() if st.session_state.get("sahay_supabase_session") else None
    if user is None:
        empty_state("📈", "Sign in to build a mood history from your check-ins and chats.")
        return

    from backend import conversations as conv_db
    try:
        mood_events = conv_db.list_mood_events(user, limit=100)
    except Exception as exc:  # noqa: BLE001
        st.error("Couldn't load your mood history right now. Please try again.")
        st.caption(f"Technical detail (dev preview only): {exc}")
        return

    if not mood_events:
        empty_state("📈", "No mood history yet — check in on the Mood Check-in page, or chat with Sahay.")
        return

    _render_charts(mood_events)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    render_section_header("Recent entries")
    for m in mood_events:
        emoji = MOOD_EMOJI.get(m.get("mood"), "🙂")
        source_label = "Check-in" if m.get("source") == "checkin" else "Chat"
        with st.container(border=True):
            row_col, del_col = st.columns([5, 1])
            with row_col:
                st.markdown(f"{emoji} **{m.get('mood', 'Neutral')}** · {source_label} · {m['created_at'][:16].replace('T', ' ')}")
                scales = []
                if m.get("stress_level") is not None:
                    scales.append(f"Stress {m['stress_level']}/5")
                if m.get("energy_level") is not None:
                    scales.append(f"Energy {m['energy_level']}/5")
                if m.get("sleep_quality") is not None:
                    scales.append(f"Sleep {m['sleep_quality']}/5")
                if scales:
                    st.caption(" · ".join(scales))
                if m.get("note"):
                    st.caption(m["note"])
            with del_col:
                if st.button("🗑️", key=f"delete_mood_{m['id']}", help="Delete this entry"):
                    conv_db.delete_mood_event(user, m["id"])
                    st.rerun()


def _render_charts(mood_events: list[dict]) -> None:
    render_section_header(
        "Mood distribution",
        description="How often each mood has been recorded — a self-reported pattern, not a diagnosis.",
    )
    counts = Counter(m["mood"] for m in mood_events if m.get("mood"))
    if counts:
        st.bar_chart(dict(counts.most_common()))
    else:
        st.caption("Not enough data yet.")

    # Trends use chronological order (oldest -> newest) so the chart reads left-to-right sensibly.
    chronological = list(reversed(mood_events))

    def _series(field: str) -> dict:
        return {i: m[field] for i, m in enumerate(chronological) if m.get(field) is not None}

    stress_series = _series("stress_level")
    energy_series = _series("energy_level")
    sleep_series = _series("sleep_quality")

    if stress_series or energy_series or sleep_series:
        render_section_header(
            "Self-reported trends",
            description=(
                "These reflect what you recorded at each check-in — for example, your "
                "recorded stress may have been higher this week than last week. This is "
                "not a clinical interpretation."
            ),
        )
        if stress_series:
            st.caption("Stress (1-5, higher = more stress)")
            st.line_chart(stress_series)
        if energy_series:
            st.caption("Energy (1-5, higher = more energy)")
            st.line_chart(energy_series)
        if sleep_series:
            st.caption("Sleep quality (1-5, higher = better sleep)")
            st.line_chart(sleep_series)

"""
components/chatbot_launcher.py
-------------------------------
Floating chatbot launcher + expandable panel.

Composition pattern (inject once near the top of the app, before the
page router, so it persists across every authenticated page) is adapted
from LearnMate AI's render_chatbot_widget() — see /PHASE0_AUDIT.md
section B.

PHASE 3 UPDATE: send_message() now calls the real
chatbot/response_generator.py pipeline (safety screening -> mood
analysis -> OpenRouter -> output screening) instead of a fixed
placeholder string. Still no conversation persistence — history lives
only in st.session_state, exactly as it did in Phase 1/2 (see
PHASE3_PRE_IMPLEMENTATION_AUDIT.md §6 for why that's the right scope for
this phase). Demo Mode still works with zero Supabase/OpenRouter calls —
generate_response() itself degrades to a friendly "not connected yet"
message whenever OPENROUTER_CONFIG isn't configured, so this component
never needs to know or care whether the user is authenticated or in Demo
Mode; it behaves identically either way.

PHASE 5 (true floating positioning): fixes the exact gap the Phase 1
audit flagged — the old `.sahay-launcher` div was `position: fixed`,
but it was a decorative, non-interactive markdown block; the real
`st.button` that actually toggled the panel sat in normal document flow
in a `st.columns([6, 1])` layout beneath it. That decorative markdown
block is REMOVED here (not moved, not restyled — the "two visible
launchers" problem is solved by deleting the one that was never
clickable). In its place, the real toggle button and the real panel
(`_render_panel()`, unchanged) are both rendered inside a single
`st.container(key="sahay_chatbot")` — Streamlit auto-generates a
`st-key-sahay_chatbot` class on that container's wrapper div, which
`_CHATBOT_FIXED_CSS` below targets directly with `position: fixed`,
the same technique LearnMate's `frontend/chatbot.py` uses for its own
`st-key-lm_chatbot` container (see PHASE5_FLOATING_CHATBOT_REPORT.md for
the full before/after and the z-index layering rationale against Phase
4's sidebar drawer).

Nothing below this point changes: send_message(), render_suggestion_card(),
render_suggestion_chips(), _render_panel(), and SUGGESTION_CHIPS are all
byte-identical to Phase 3 — safety screening, mood analysis, OpenRouter,
and conversation state (`sahay_chat_history`, `sahay_chat_open`) are
untouched. Only render_chatbot_launcher()'s wrapper changed.
"""

from __future__ import annotations

import streamlit as st

from components.theme import sahay_icon_html, COLORS

# ---------------------------------------------------------------------------
# Fixed-position CSS for the floating companion (Phase 5).
#
# Self-contained here (not added to components/theme.py) — same pattern
# Phase 3/4 used for their own page-scoped CSS, and keeps this phase's
# change confined to this one file. Targets the Streamlit-auto-generated
# `st-key-sahay_chatbot` class rather than any hand-applied class, since
# the whole point is fixing the REAL interactive container, not another
# decorative div.
#
# z-index: 999 — reused from the old `.sahay-launcher` value for
# continuity, and deliberately LOWER than Phase 4's sidebar-drawer stack
# (backdrop 999997, drawer 999998, drawer-toggle 1000000): on mobile,
# when the nav drawer is open, the drawer/backdrop must sit above the
# chatbot per the Phase 5 spec ("chatbot should not obscure the
# navigation drawer") — 999 already sits comfortably below all three, so
# no extra conditional CSS is needed for that case. 999 is also far
# below where Streamlit's own native dialogs/modals render, so it can't
# interfere with those either.
# ---------------------------------------------------------------------------
def _fixed_chatbot_css() -> str:
    dark = st.session_state.get("sahay_dark_mode", False)
    panel_bg = COLORS["card_dark"] if dark else COLORS["card_light"]
    panel_border = COLORS["border_dark"] if dark else COLORS["border_light"]
    panel_shadow = COLORS["shadow_dark"] if dark else COLORS["shadow_light"]
    gradient = (
        f"linear-gradient(120deg, {COLORS['deep_blue']} 0%, "
        f"{COLORS['lavender']} 55%, {COLORS['soft_teal']} 100%)"
    )
    return f"""
    <style>
    div[class*="st-key-sahay_chatbot"] {{
        position: fixed !important;
        bottom: 22px;
        right: 22px;
        z-index: 999;
        width: min(360px, 92vw);
        max-height: 78vh;
        overflow-y: auto;
        background: {panel_bg};
        border: 1px solid {panel_border};
        border-radius: 18px;
        box-shadow: {panel_shadow};
        padding: 14px 16px;
    }}
    /* The toggle button (always the first button in this container) —
       compact, gradient, pill-shaped, reads as "the launcher" whether
       the panel is open or closed. Any buttons rendered *inside* the
       panel (suggestion chips, dismiss, clear) are NOT first-of-type,
       so they keep their normal theme.py button styling underneath. */
    div[class*="st-key-sahay_chatbot"] .stButton:first-of-type > button {{
        background: {gradient} !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 999px !important;
        font-weight: 600;
        box-shadow: 0 6px 18px rgba(47,93,138,0.30);
    }}
    @media (max-width: 768px) {{
        div[class*="st-key-sahay_chatbot"] {{
            right: 12px;
            bottom: 12px;
            width: 90vw;
            max-height: 70vh;
        }}
    }}
    </style>
    """

# Shared with pages/companion.py so both surfaces offer the same starting
# points. Clicking a chip sends it through the exact same
# generate_response() pipeline as typed input — no shortcut around
# safety/mood/OpenRouter.
SUGGESTION_CHIPS = [
    "Help me relax",
    "I'm stressed about exams",
    "I feel overwhelmed",
    "I need motivation",
]


def send_message(history_key: str, text: str, agent: str = "companion") -> None:
    """Append a user message + Sahay's real generated reply to the given
    session_state history list. Shared by the launcher panel, the
    full-page companion, and suggestion chips on both.

    Uses st.session_state.get("sahay_language", "English") so a language
    choice made on the full-page companion (see pages/companion.py)
    applies to the floating launcher too, without this module needing
    its own language selector — kept minimal per the "don't redesign the
    UI unnecessarily" instruction.

    PHASE 1 (Agentic AI upgrade — role separation via prompts only):
    `agent` defaults to "companion" — every existing call site that
    doesn't pass it (pages/companion.py's Demo Mode) keeps today's exact
    behavior unchanged. This module's own internal calls (see
    _render_panel() below) pass agent="navigator" explicitly, since the
    floating widget is the Navigator surface.

    PHASE 5 (Option B): also stores result.get("action") on the history
    turn, alongside the existing mood/safety_action/suggestion fields —
    additive only, same .get()-based pattern as the others.
    """
    from chatbot.response_generator import generate_response  # local import: keeps this UI
    # module free of a hard import-time dependency on the AI engine, matching how
    # backend.auth is only imported where actually needed elsewhere in this codebase.

    st.session_state[history_key].append({"role": "user", "content": text})
    language = st.session_state.get("sahay_language", "English")
    history_before = st.session_state[history_key][:-1]  # exclude the message just added

    # PHASE 7: pass user_id ONLY for safety-event monitoring (never for
    # persistence — the launcher still never writes chat history to
    # Supabase, matching its established design). Demo Mode has no real
    # session, so this stays None there, and _log_safety_event_if_authenticated()
    # is a no-op for None — Demo Mode still never touches Supabase in any form.
    user_id = None
    if st.session_state.get("sahay_supabase_session"):
        from backend.auth import get_current_user
        current_user = get_current_user()
        user_id = current_user.id if current_user else None

    result = generate_response(text, chat_history=history_before, language=language, user_id=user_id, agent=agent)
    st.session_state[history_key].append({
        "role": "assistant",
        "content": result["reply"],
        "mood": result.get("mood"),
        "safety_action": result.get("safety_action"),
        "suggestion": result.get("suggestion"),
        "action": result.get("action"),
    })


def render_suggestion_card(history_key: str, key_prefix: str) -> None:
    """PHASE 5: renders a dismissible 'Try this now' card for the most
    recent assistant turn only — never for every message (the mapping in
    chatbot/mood_analyzer.MOOD_SUGGESTIONS already naturally excludes
    Happy/Calm/Neutral, and this function additionally only ever looks
    at the LAST turn, so even a run of Stressed messages shows the card
    once per new reply, not stacked). Never shown for a crisis/blocked
    turn — chatbot/response_generator.py guarantees `suggestion` is None
    on those paths, so there's nothing to check here beyond "does the
    last turn have one."

    Dismissal is tracked per message index in
    st.session_state[f"{key_prefix}_dismissed_suggestions"], a set —
    once dismissed, that specific turn's card won't reappear, but a
    *new* reply's card (a different index) can still show.
    """
    history = st.session_state.get(history_key, [])
    if not history or history[-1]["role"] != "assistant":
        return
    suggestion = history[-1].get("suggestion")
    if not suggestion:
        return

    dismissed_key = f"{key_prefix}_dismissed_suggestions"
    st.session_state.setdefault(dismissed_key, set())
    turn_index = len(history) - 1
    if turn_index in st.session_state[dismissed_key]:
        return

    from chatbot.mood_analyzer import MOOD_EMOJI
    mood = history[-1].get("mood") or {}
    emoji = MOOD_EMOJI.get(mood.get("mood"), "💡")

    with st.container(border=True):
        st.markdown(f"{emoji} **Try this now**")
        st.write(suggestion["text"])
        c1, c2 = st.columns([1, 1])
        with c1:
            if suggestion.get("activity_key") and st.button(
                "Open Relaxation", key=f"{key_prefix}_suggestion_open_{turn_index}", use_container_width=True
            ):
                st.session_state["sahay_page"] = "relaxation"
                st.rerun()
        with c2:
            if st.button("Dismiss", key=f"{key_prefix}_suggestion_dismiss_{turn_index}", use_container_width=True):
                st.session_state[dismissed_key].add(turn_index)
                st.rerun()


def render_navigation_action_card(history_key: str, key_prefix: str) -> None:
    """PHASE 5 (Option B — Navigator page-navigation suggestions).

    Renders a dismissible 'Want to go there?' card for the most recent
    assistant turn ONLY, mirroring render_suggestion_card()'s pattern
    but reading the separate `action` field instead of `suggestion` —
    kept fully independent so the existing Relaxation suggestion-card
    behavior above is not touched by this addition in any way.

    `action` is set by chatbot/response_generator.py's generate_response()
    ONLY when the Navigator agent's open_page tool returned a valid,
    allowlisted page — the page_key/label shown here always come from
    that already-validated data (see chatbot/tools.py: open_page()),
    never from arbitrary model text.

    Navigation happens ONLY when the student clicks the button below —
    nothing in this module (or anywhere in chatbot/) sets
    st.session_state["sahay_page"] or calls st.rerun() on its own.

    Dismissal is tracked separately from the Relaxation suggestion card,
    in its own st.session_state[f"{key_prefix}_dismissed_actions"] set.
    """
    history = st.session_state.get(history_key, [])
    if not history or history[-1]["role"] != "assistant":
        return
    action = history[-1].get("action")
    if not action or action.get("type") != "open_page" or not action.get("page_key"):
        return

    dismissed_key = f"{key_prefix}_dismissed_actions"
    st.session_state.setdefault(dismissed_key, set())
    turn_index = len(history) - 1
    if turn_index in st.session_state[dismissed_key]:
        return

    label = action.get("label") or action["page_key"]

    with st.container(border=True):
        st.markdown("🧭 **Want to go there?**")
        st.write(f"I can take you to **{label}**.")
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button(f"Open {label}", key=f"{key_prefix}_action_open_{turn_index}", use_container_width=True):
                st.session_state["sahay_page"] = action["page_key"]
                st.rerun()
        with c2:
            if st.button("Not now", key=f"{key_prefix}_action_dismiss_{turn_index}", use_container_width=True):
                st.session_state[dismissed_key].add(turn_index)
                st.rerun()


def render_suggestion_chips(history_key: str, key_prefix: str, agent: str = "companion") -> None:
    cols = st.columns(len(SUGGESTION_CHIPS))
    for i, chip in enumerate(SUGGESTION_CHIPS):
        with cols[i]:
            if st.button(chip, key=f"{key_prefix}_chip_{i}", use_container_width=True):
                send_message(history_key, chip, agent=agent)
                st.rerun()


def render_chatbot_launcher() -> None:
    st.session_state.setdefault("sahay_chat_open", False)
    st.session_state.setdefault("sahay_chat_history", [])

    st.markdown(_fixed_chatbot_css(), unsafe_allow_html=True)

    # PHASE 5: the real toggle button AND the real panel now both live
    # inside the SAME st.container(key="sahay_chatbot") — the container
    # itself is what's position:fixed (see _fixed_chatbot_css() above),
    # so the actual clickable element is genuinely pinned to the
    # viewport, not just a decorative div beside it. There is exactly
    # one visible launcher control: this button. No separate markdown
    # pill is rendered anywhere else.
    with st.container(key="sahay_chatbot"):
        is_open = st.session_state["sahay_chat_open"]
        toggle_label = "✖️  Close Sahay" if is_open else "💬  Sahay AI"
        if st.button(toggle_label, key="sahay_launcher_toggle", help="Open or close the Sahay AI companion"):
            st.session_state["sahay_chat_open"] = not st.session_state["sahay_chat_open"]
            st.rerun()

        if st.session_state["sahay_chat_open"]:
            _render_panel()


def _render_panel() -> None:
    with st.container(border=True):
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;'>"
            f"{sahay_icon_html(24)}"
            f"<span style='font-weight:700;'>Sahay</span>"
            f"<span style='color:#6B7280;font-size:12px;'>· AI wellness companion, not a medical professional</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        for turn in st.session_state["sahay_chat_history"]:
            with st.chat_message(turn["role"]):
                st.write(turn["content"])

        render_suggestion_card("sahay_chat_history", key_prefix="launcher")
        render_navigation_action_card("sahay_chat_history", key_prefix="launcher")

        if not st.session_state["sahay_chat_history"]:
            render_suggestion_chips("sahay_chat_history", key_prefix="launcher", agent="navigator")

        user_msg = st.chat_input("Message Sahay")
        if user_msg:
            send_message("sahay_chat_history", user_msg, agent="navigator")
            st.rerun()

        if st.session_state["sahay_chat_history"]:
            if st.button("Clear conversation", key="sahay_clear_chat"):
                st.session_state["sahay_chat_history"] = []
                st.rerun()

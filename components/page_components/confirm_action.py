"""
components/page_components/confirm_action.py
------------------------------------------------
PHASE 6B: a reusable "click to reveal a warning + Yes/Cancel" confirm
flow, adapted from a pattern repeated three times today (see
PHASE6A_INDIVIDUAL_PAGE_AUDIT.md §8/§10): pages/privacy.py's two
delete-data confirmations, and pages/companion.py's "Clear all history"
confirmation — all three follow the exact same
trigger-button -> warning -> Yes/Cancel shape.

This component ONLY manages whether the warning/Yes/Cancel is currently
shown, and reports which button was clicked. It never calls a delete
function itself — the calling page remains entirely responsible for
what "confirm" means (e.g. `conv_db.delete_all_conversations(user)`),
per the "components don't touch data" rule. It keeps its own
open/closed flag under a component-private key
(`_confirm_action_open__<key>`) so it cannot collide with — and does
not replace — any existing page-level confirm flag
(`privacy_confirm_convos`, `sahay_confirm_clear_all`, etc.); those stay
exactly as they are until/unless a page is migrated to use this
component in a later phase.
"""

from __future__ import annotations

import streamlit as st


def render_confirm_action(
    trigger_label: str,
    warning_text: str,
    key: str,
    confirm_label: str = "Yes, delete",
    cancel_label: str = "Cancel",
) -> str:
    """Render a trigger button that reveals a warning + Yes/Cancel pair.

    Args:
        trigger_label: the page's existing trigger-button text (e.g.
            "Delete all conversation history").
        warning_text: the page's existing warning copy shown once
            revealed (e.g. "This permanently deletes every saved
            conversation and its messages.") — never reworded here.
        key: a caller-supplied unique string identifying this
            particular confirm flow (e.g. "privacy_delete_conversations").
        confirm_label / cancel_label: existing button labels.

    Returns:
        "confirm" the run the Yes button is clicked, "cancel" the run
        Cancel is clicked, "none" otherwise. The caller performs the
        actual action (and any success/error messaging) itself.
    """
    open_key = f"_confirm_action_open__{key}"
    st.session_state.setdefault(open_key, False)

    if not st.session_state[open_key]:
        if st.button(trigger_label, key=f"confirm_action_trigger__{key}"):
            st.session_state[open_key] = True
            st.rerun()
        return "none"

    st.warning(warning_text)
    result = "none"
    c1, c2 = st.columns(2)
    with c1:
        if st.button(confirm_label, key=f"confirm_action_yes__{key}", type="primary", use_container_width=True):
            st.session_state[open_key] = False
            result = "confirm"
    with c2:
        if st.button(cancel_label, key=f"confirm_action_cancel__{key}", use_container_width=True):
            st.session_state[open_key] = False
            result = "cancel"
    return result

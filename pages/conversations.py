"""pages/conversations.py — PHASE 4: full conversation list (same data as
the Sahay Companion page's history panel), with a link to open each in
the Companion page. Kept as a separate nav destination since the master
spec lists "Conversation History" as its own sidebar item.

PHASE 6D: header swapped to components.page_components.render_page_header
(no description added — none existed before). The per-conversation row
— previously a manual `st.container(border=True)` +
`st.columns([4, 1])` + markdown/caption + a raw `st.button("Open",
key=f"convlist_open_{c['id']}")` — is now a single
components.page_components.render_list_row call. This is the exact
"Conversations-shape" list_row was built and stub-tested for in Phase
6B (static title/caption + one separate trailing action button, no
title-is-button, no secondary icon). The widget key
(`convlist_open_{c['id']}`), the two session-state writes
(`sahay_active_conversation_id`, `sahay_page`), and the `st.rerun()`
call are all unchanged — only *how* the click is detected changed, from
a raw `st.button(...)` return value to `render_list_row(...)`'s
`action_clicked` return value. `auth.get_current_user()`,
`backend.conversations.list_conversations(user)`, and both
`empty_state(...)` calls (no user / no conversations) are byte-identical
to before."""

from __future__ import annotations

import streamlit as st

from components.cards import empty_state
from components.page_components.page_header import render_page_header
from components.page_components.list_row import render_list_row
from backend import auth


def render() -> None:
    render_page_header("Conversation History")

    user = auth.get_current_user() if st.session_state.get("sahay_supabase_session") else None
    if user is None:
        empty_state("🗂️", "Sign in to save and revisit your conversations. In Demo Mode, conversations aren't saved.")
        return

    from backend import conversations as conv_db
    try:
        convo_list = conv_db.list_conversations(user)
    except Exception as exc:  # noqa: BLE001
        st.error("Couldn't load your conversations right now. Please try again.")
        st.caption(f"Technical detail (dev preview only): {exc}")
        return

    if not convo_list:
        empty_state("🗂️", "No conversations yet — start one from the Sahay Companion page.")
        return

    for c in convo_list:
        opened, _ = render_list_row(
            c["title"] or "New conversation",
            caption=f"Last updated {c['updated_at'][:10]}",
            action_label="Open",
            action_key=f"convlist_open_{c['id']}",
        )
        if opened:
            st.session_state["sahay_active_conversation_id"] = c["id"]
            st.session_state["sahay_page"] = "companion"
            st.rerun()


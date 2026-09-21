"""
components/page_components/list_row.py
-----------------------------------------
PHASE 6B: a reusable "title + caption + trailing action(s)" row, adapted
from the Phase 6A audit's single strongest duplication finding (see
PHASE6A_INDIVIDUAL_PAGE_AUDIT.md §7/§8) — three slightly different
shapes of near-identical markup currently repeated in:
  - pages/conversations.py: static title/caption text + a separate
    "Open" trailing button.
  - pages/companion.py's conversation-history rows: the title itself
    IS the clickable button (primary-styled when it's the active
    conversation) + a separate 🗑️ delete icon button.
  - pages/mood_history.py's entry rows: static summary text + a 🗑️
    delete icon button only, no primary action at all.

This component only renders the row and reports which control (if any)
was clicked THIS run — it never performs the navigation/delete/rename
itself; the calling page stays entirely responsible for what a click
means. No page currently imports this (pages are migrated in a later,
separately-approved phase); this file introduces no session-state key
of its own.
"""

from __future__ import annotations

import streamlit as st


def render_list_row(
    title: str,
    caption: str | None = None,
    title_is_button: bool = False,
    action_label: str | None = None,
    action_key: str = "",
    secondary_icon: str | None = None,
    secondary_key: str = "",
    secondary_help: str | None = None,
    active: bool = False,
) -> tuple[bool, bool]:
    """Render one list row inside a bordered container.

    Args:
        title: the row's existing primary text (e.g. a conversation
            title, or "{emoji} {mood} · {source} · {date}").
        caption: the row's existing secondary text, if any. Ignored
            when `title_is_button=True` (a button label can't carry a
            separate caption line underneath it — matches how
            pages/companion.py's history rows already work today).
        title_is_button: if True, the title itself is rendered as the
            clickable primary control (pages/companion.py's shape) and
            `action_label`/`action_key` are ignored. If False (the
            default), the title is static text and an optional separate
            `action_label` button is rendered instead
            (pages/conversations.py's shape). Leave both unset for a
            text-only row with no primary action
            (pages/mood_history.py's shape).
        action_label / action_key: label + unique caller-supplied
            widget key for a separate trailing primary button, used
            only when `title_is_button=False`.
        secondary_icon / secondary_key / secondary_help: label/key/tooltip
            for an optional second, smaller trailing button (e.g. "🗑️").
            Independent of the primary action — a row can have both.
        active: whether this row is the currently-selected item — the
            primary control (title-button or action_label button) is
            styled `type="primary"` instead of `type="secondary"`, the
            same highlight pages/companion.py's history panel already
            uses for the open conversation.

    Returns:
        (action_clicked, secondary_clicked) — booleans for this run
        only. Neither triggers any state change inside this component.
    """
    action_clicked = False
    secondary_clicked = False
    button_type = "primary" if active else "secondary"

    with st.container(border=True):
        if title_is_button:
            row_col, sec_col = st.columns([4, 1]) if secondary_icon else (st.container(), None)
            with row_col:
                action_clicked = st.button(
                    title, key=action_key, use_container_width=True, type=button_type,
                )
        else:
            row_col, sec_col = st.columns([4, 1]) if (action_label or secondary_icon) else (st.container(), None)
            with row_col:
                st.markdown(f"**{title}**")
                if caption:
                    st.caption(caption)
            if action_label and sec_col is not None:
                with sec_col:
                    action_clicked = st.button(
                        action_label, key=action_key, use_container_width=True, type=button_type,
                    )

        if secondary_icon:
            with sec_col:
                secondary_clicked = st.button(secondary_icon, key=secondary_key, help=secondary_help)

    return action_clicked, secondary_clicked

"""
components/page_components/section_header.py
------------------------------------------------
PHASE 6B: a lightweight sub-section heading (title + optional
description), replacing the `st.markdown("##### ...")` (+ optional
`st.caption(...)`) pattern repeated across most of the 14 pages —
e.g. Wellness Dashboard's "Approximate mood distribution"/"Self-reported
wellness trends", Mood History's "Recent entries", Companion's "Recent
Conversations", Human Help's "Normal support"/"Urgent support"/"Crisis &
support resources", Privacy's five explanatory headings, Settings'
"Send feedback" (see PHASE6A_INDIVIDUAL_PAGE_AUDIT.md §8).

Deliberately tiny — per the Phase 6B instructions ("keep it lightweight
... do not make it a giant component"). No icon/badge/action support;
that's what page_header.py is for at the page level. If a sub-section
ever needs those, use page_header.py again rather than growing this one.

PHASE (HTML-rendering bug fix, approved): same fix as
page_header.py — the HTML is now built as one continuous string
instead of a multi-line indented f-string, so an unset `description`
(most calls) can no longer leave a blank line that breaks Streamlit's
raw-HTML-block detection and makes the tags render as visible literal
text. Same tags/classes/content as before.
"""

from __future__ import annotations

import streamlit as st

from components.theme import COLORS


def render_section_header(title: str, description: str | None = None) -> None:
    """Render a sub-section heading.

    Args:
        title: the page's existing sub-heading text.
        description: the page's existing caption/explanatory text for
            this sub-section, if any.
    """
    dark = st.session_state.get("sahay_dark_mode", False)
    muted = COLORS["muted_dark"] if dark else COLORS["muted_light"]

    description_html = (
        f'<div style="color:{muted};font-size:13px;margin-top:2px;">{description}</div>'
        if description else ""
    )
    html = (
        '<div style="margin:14px 0 4px 0;">'
        f'<div style="font-weight:700;font-size:15px;">{title}</div>'
        f"{description_html}"
        "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)

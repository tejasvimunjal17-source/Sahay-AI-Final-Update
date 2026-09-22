"""pages/government_services.py — PHASE 4: polished rendering of
content/government_services.py's five-section structure (what/who/how/
official link/note). No URLs, phone numbers, eligibility rules, or
procedures are invented anywhere in this file — every fact-shaped claim
comes from the content module, which you edit directly.

PHASE 6C: header swapped from a hand-rolled `st.markdown("### ...")` to
the shared components.page_components.page_header — the "🇮🇳" that used
to be inline in the title string is now the header's `icon` argument.

CONTROLLED UI ENHANCEMENT TASK (visual reference: LearnMate's Government
& Student Support Services page): cards now render in a two-column grid
on wide screens (falls back to one column automatically on narrow ones,
since it's just two st.columns wrapping each pair of services — Streamlit
stacks columns vertically below its own built-in mobile breakpoint, so
no new CSS breakpoint is needed here), and the "Open official portal"
link is now `type="primary"`, which reuses the app's EXISTING global
gradient button styling (components/theme.py's `--sahay-gradient` rule,
extended in that same file to also cover `.stLinkButton > a[kind="primary"]`
— not a new, page-scoped, duplicate CSS block). This is presentation
only: the same GOVERNMENT_SERVICES import, the same fields, the same
fallback strings, the same official URLs, and the same "pending
verification" logic as before — nothing about the underlying data
changed."""

from __future__ import annotations

import streamlit as st

from components.cards import safety_note
from components.page_components.page_header import render_page_header
from content.government_services import GOVERNMENT_SERVICES


def _render_service_card(service: dict, index: int) -> None:
    with st.container(key=f"govservice_card_{index}", border=True):
        st.markdown(f"#### {service['icon']} {service['name']}")

        st.markdown("**What it is**")
        st.write(service["what_it_is"])

        st.markdown("**Who it may be for**")
        st.write(service["intended_for"])

        st.markdown("**How to access it**")
        st.write(service.get("how_to_access", "See the official portal for current steps."))

        st.markdown("**Official website**")
        if service.get("official_url"):
            st.link_button(
                "🔗 Visit Official Portal",
                service["official_url"],
                use_container_width=True,
                type="primary",
            )
        else:
            st.caption("⚠️ Official portal link pending verification — not yet added.")

        if service.get("important_note"):
            st.caption(f"ℹ️ {service['important_note']}")


def render() -> None:
    render_page_header("Government & Student Support Services", icon="🇮🇳")
    safety_note(
        "This section provides general guidance only. Sahay AI is not an "
        "official representative of the Government of India and cannot "
        "issue any ID, card, certificate, or prescription. Always verify "
        "current details on the official portal before acting — eligibility, "
        "documents, and procedures may change."
    )

    # Two-column grid, one pair of services per row — falls back to a
    # naturally readable single column on narrow/mobile widths the same
    # way every other two-column layout in this app already does
    # (Streamlit stacks st.columns() vertically below its own built-in
    # mobile breakpoint; no new CSS breakpoint is needed for this).
    for i in range(0, len(GOVERNMENT_SERVICES), 2):
        pair = GOVERNMENT_SERVICES[i:i + 2]
        cols = st.columns(2)
        for offset, (col, service) in enumerate(zip(cols, pair)):
            with col:
                _render_service_card(service, i + offset)


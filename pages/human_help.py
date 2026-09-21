"""pages/human_help.py — PHASE 5: restructured into two visually distinct
tiers (Normal Support / Urgent Support) per the approved audit, calm
visual hierarchy — the normal-support section stays low-key; the urgent
section is the only place with any warning styling, so the rest of the
app never looks like an emergency screen. Crisis resources still render
from content/crisis_resources.py (still empty by default — nothing
invented), same graceful-empty-list handling as chatbot/safety.py.

PHASE 6C: header swapped to components.page_components.page_header (no
description added — none existed before). The three
`st.markdown("##### ...")` sub-headings are now
components.page_components.section_header calls with identical text
(the "🚨" stays inline in the Urgent Support title string, since
section_header has no separate icon argument by design — see its own
docstring). Normal Support's and Urgent Support's rows — previously
`st.markdown(f"**{x}**")` + `st.caption(y)` inside
`st.container(border=True)`, with no button — are now
components.page_components.list_row calls with the exact same two text
fields and zero action buttons; the rendered markup is unchanged. The
`st.error(...)` crisis banner and the Crisis & Support Resources
loop/warning are byte-identical to before — CRISIS_RESOURCES entries
carry three distinct text fields (name/description/contact-availability-
region) that don't fit list_row's simpler title+caption shape, so they
were deliberately left as their existing bordered containers rather
than forced into list_row."""

from __future__ import annotations

import streamlit as st

from components.cards import safety_note
from components.page_components.page_header import render_page_header
from components.page_components.section_header import render_section_header
from components.page_components.list_row import render_list_row
from content.crisis_resources import CRISIS_RESOURCES

NORMAL_SUPPORT = [
    ("A trusted friend", "When you just need someone to listen, or to not feel alone with something."),
    ("Family member", "When you want support from someone who knows you well."),
    ("Teacher or college mentor", "When academic stress, deadlines, or a specific class is the main issue."),
    ("College support service", "For academic accommodations, advising, or campus-specific resources."),
    ("Counselor or qualified mental-health professional", "When feelings are lasting, intense, or affecting daily life — they can help in ways Sahay can't."),
]

URGENT_SUPPORT = [
    ("Immediate danger to yourself", "Contact local emergency services or a trusted person right now — don't wait."),
    ("Thoughts of self-harm or suicide", "Reach out immediately to emergency services, a crisis line, or someone you trust."),
    ("Risk of harm to someone else", "Contact local emergency services immediately."),
    ("A serious medical emergency", "Contact local emergency services or go to the nearest emergency room."),
]


def render() -> None:
    render_page_header("Human Help")
    safety_note(
        "Sahay AI is an AI wellness companion — not a therapist, doctor, or crisis "
        "service — and does not replace professional or emergency support."
    )

    render_section_header("Normal support — when you'd like someone to talk to")
    for who, when in NORMAL_SUPPORT:
        render_list_row(who, caption=when)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    render_section_header("🚨 Urgent support — if there's immediate danger")
    st.error(
        "If you are in immediate danger, please contact local emergency services "
        "or a trusted person right away — this is the one part of Sahay that's "
        "meant to stand out."
    )
    for situation, action in URGENT_SUPPORT:
        render_list_row(situation, caption=action)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    render_section_header("Crisis & support resources")

    if CRISIS_RESOURCES:
        for r in CRISIS_RESOURCES:
            with st.container(border=True):
                st.markdown(f"**{r['name']}**")
                st.write(r.get("description", ""))
                st.caption(f"{r.get('contact', '')} · {r.get('availability', '')} · {r.get('region', '')}")
    else:
        st.warning(
            "Verified crisis and counseling resources will be added here once "
            "confirmed from official sources — none are populated yet, to avoid "
            "displaying unverified information. If you're a student in India, "
            "your campus counseling office or a trusted teacher, family member, "
            "or friend is a good place to start right now."
        )


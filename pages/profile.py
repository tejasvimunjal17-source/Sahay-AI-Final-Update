"""pages/profile.py — PHASE 2: reads/updates the real `profiles` row for a
signed-in user via the anon-key client (RLS-scoped to auth.uid()). In
Demo Mode (no real session), falls back to Phase 1's disabled placeholder
fields — Demo Mode never reads or writes Supabase.

PHASE 6F: header swapped to components.page_components.render_page_header
(no description added — none existed before). No widget keys exist on
this page (the text_input/selectbox/form/form_submit_button all use
Streamlit's default auto-generated keys, both before and after), so
there was nothing to preserve there beyond confirming that fact. The
Demo Mode disabled-placeholder branch, the auth/profile-fetch branch,
the profile form, and the exact `client.table("profiles").update(...)
.eq("id", user.id).execute()` call and its two fields are all
byte-identical to before.

USER-DASHBOARD UPGRADE (this task, Part 2): reproduces the parts of
LearnMate AI's "My Profile" tab that have a genuine Sahay AI data
source, ADDED above the untouched form (nothing below this comment
block touches the Demo Mode branch, the fetch branch, or the form
logic above — see _render_profile_overview/_render_activity_links,
called once each, right before the existing `st.caption(f"Signed in
as {user.email}")` line):
- A profile header card (display name + email — the same source the
  form already edits) and three real stat chips: "Member since"
  (profiles.created_at, already stored, never surfaced before),
  "Current streak" (reuses backend.streak.get_user_streak() exactly as
  components/topbar.py does — no second streak implementation), and
  "Conversations" (a live count via the same
  backend.conversations.list_conversations() pages/conversations.py
  already calls).
- A "Your activity" row of buttons to Conversations / Mood History /
  Reports, using the same `st.session_state["sahay_page"] = <key>;
  st.rerun()` navigation pattern pages/overview.py's own "Open Sahay
  Companion" button already uses. This intentionally links to Sahay's
  existing dedicated history pages instead of rebuilding a duplicate
  history viewer inside Profile.
No new table; every figure is read from data this codebase already
stores. Any individual fetch that fails degrades to "—", never a
fabricated number, and never blocks the rest of the page.
"""

from __future__ import annotations

import streamlit as st

from components.page_components.page_header import render_page_header
from backend import auth


def _format_member_since(raw) -> str | None:
    if not raw:
        return None
    try:
        from datetime import datetime
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).strftime("%d %b %Y")
    except Exception:  # noqa: BLE001
        return None


def _render_profile_overview(user, profile: dict) -> None:
    display_name = profile.get("display_name") or user.email or "Sahay AI user"

    conversation_count = "—"
    try:
        from backend import conversations as conv_db
        conversation_count = str(len(conv_db.list_conversations(user)))
    except Exception:  # noqa: BLE001
        pass

    streak_label = "—"
    try:
        from backend import conversations as conv_db
        from backend.streak import get_user_streak
        streak_label = str(get_user_streak(user, conv_db).current_streak)
    except Exception:  # noqa: BLE001
        pass

    member_since = _format_member_since(profile.get("created_at")) or "—"

    st.markdown(
        f"""
        <div class="sahay-card">
            <div class="sahay-card-muted-label">MY PROFILE</div>
            <p style="font-size:22px;font-weight:700;margin:2px 0 2px 0;">{display_name}</p>
            <div class="sahay-card-caption">{user.email or ''}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    for col, label, value in (
        (c1, "MEMBER SINCE", member_since),
        (c2, "CURRENT STREAK", f"🔥 {streak_label}"),
        (c3, "CONVERSATIONS", conversation_count),
    ):
        with col:
            st.markdown(
                f'<div class="sahay-card"><div class="sahay-card-muted-label">{label}</div>'
                f'<p class="sahay-card-metric" style="font-size:18px;">{value}</p></div>',
                unsafe_allow_html=True,
            )


def _render_activity_links() -> None:
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    st.markdown("##### Your activity")
    links = [
        ("💬 Conversation History", "conversations"),
        ("📈 Mood History", "mood_history"),
        ("📄 Reports", "reports"),
    ]
    cols = st.columns(len(links))
    for col, (label, page_key) in zip(cols, links):
        with col:
            if st.button(label, key=f"profile_link_{page_key}", use_container_width=True):
                st.session_state["sahay_page"] = page_key
                st.rerun()
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)


def render() -> None:
    render_page_header("Profile")

    user = auth.get_current_user() if st.session_state.get(
        "sahay_supabase_session"
    ) else None

    if user is None:
        st.text_input("Display name", placeholder="Not available in Demo Mode", disabled=True)
        st.selectbox("Preferred language", ["English", "Hindi", "Hinglish"], disabled=True)
        st.caption("Sign in (see the landing page) to create and edit a real profile.")
        return

    try:
        profile = auth.get_profile(user)
    except Exception as exc:  # noqa: BLE001
        st.error("Couldn't load your profile right now. Please try again.")
        st.caption(f"Technical detail (dev preview only): {exc}")
        return

    if profile is None:
        st.warning("No profile found for your account yet. Try refreshing the page.")
        return

    _render_profile_overview(user, profile)
    _render_activity_links()

    st.caption(f"Signed in as {user.email}")

    with st.form("profile_form"):
        display_name = st.text_input("Display name", value=profile.get("display_name") or "")
        languages = ["English", "Hindi", "Hinglish"]
        current_lang_code = profile.get("preferred_language") or "en"
        lang_labels = {"en": "English", "hi": "Hindi", "hinglish": "Hinglish"}
        current_label = lang_labels.get(current_lang_code, "English")
        preferred_language = st.selectbox(
            "Preferred language", languages,
            index=languages.index(current_label) if current_label in languages else 0,
        )
        submitted = st.form_submit_button("Save changes", type="primary")

    if submitted:
        lang_code = {"English": "en", "Hindi": "hi", "Hinglish": "hinglish"}[preferred_language]
        try:
            client = auth.get_client_for_current_user()
            client.table("profiles").update({
                "display_name": display_name,
                "preferred_language": lang_code,
            }).eq("id", user.id).execute()
            st.success("Profile updated.")
        except Exception as exc:  # noqa: BLE001
            st.error("Couldn't save your changes right now. Please try again.")
            st.caption(f"Technical detail (dev preview only): {exc}")

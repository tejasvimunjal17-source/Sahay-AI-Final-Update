"""pages/profile.py — "My Profile": header card, real account stats, quick
links, edit form, and account actions.

DATA RULES (unchanged from earlier phases):
- Signed-in users only ever see their OWN `profiles` row, read/updated via
  the anon-key, RLS-scoped client (backend.auth). No internal IDs, tokens
  or service-role data are displayed.
- Demo Mode (no real session) never calls Supabase: it shows an honest
  "no account" card plus the same disabled placeholder fields as before.
- Every statistic comes from data Sahay already stores (conversations,
  mood_events, wellness_activity_logs, profiles.created_at). A failed
  fetch shows "—", never 0. Counts that hit the fetch limit show "N+".
- The streak reuses backend.streak.get_user_streak() — the same
  implementation the global top-right streak popover uses. There is no
  second streak implementation here.

PROFILE UPGRADE: adds email/account display, "Mood check-ins" and
"Wellness activities" stats, quick links to existing pages, a Log out
action (same logic as the sidebar's), HTML-escaping of user-controlled
text, and a refresh after saving so the sidebar name updates at once.
The `profiles` update call and its two fields are unchanged. No new
tables, columns, or migrations.
"""

from __future__ import annotations

import html

import streamlit as st

from components.page_components.page_header import render_page_header
from components.page_components.section_header import render_section_header
from components.sidebar import ALL_PAGE_KEYS
from backend import auth

_FETCH_LIMIT = 500  # same cap backend.streak uses for mood/activity reads
_SAVED_FLASH_KEY = "_sahay_profile_saved"

_QUICK_LINKS = [
    ("💬 Sahay Companion", "companion"),
    ("📈 Mood History", "mood_history"),
    ("🗂️ Conversations", "conversations"),
    ("📊 Wellness Dashboard", "wellness_dashboard"),
    ("📄 Reports", "reports"),
    ("🇮🇳 Government Services", "government_services"),
    ("🔒 Privacy", "privacy"),
    ("⚙️ Settings", "settings"),
]

_LANG_LABELS = {"en": "English", "hi": "Hindi", "hinglish": "Hinglish"}

_PROFILE_CSS = """
<style>
.sahay-profile-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:0 0 16px 0;}
.sahay-profile-stats .sahay-card{margin:0;padding:16px 18px;min-width:0;}
.sahay-profile-stats .sahay-card-metric{font-size:22px;overflow-wrap:anywhere;}
.sahay-profile-header p,.sahay-profile-header div{overflow-wrap:anywhere;}
</style>
"""


def _esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def _format_member_since(raw) -> str | None:
    if not raw:
        return None
    try:
        from datetime import datetime
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).strftime("%d %b %Y")
    except Exception:  # noqa: BLE001
        return None


def _capped(count: int, limit: int) -> str:
    return f"{limit}+" if count >= limit else str(count)


def _load_stats(user) -> dict[str, str]:
    """Each figure is fetched independently; any failure leaves that one
    figure as "—" without affecting the others or the rest of the page."""
    stats = {"streak": "—", "conversations": "—", "checkins": "—", "activities": "—"}
    try:
        from backend import conversations as conv_db
    except Exception:  # noqa: BLE001
        return stats

    try:
        stats["conversations"] = str(len(conv_db.list_conversations(user)))
    except Exception:  # noqa: BLE001
        pass
    try:
        moods = conv_db.list_mood_events(user, limit=_FETCH_LIMIT)
        checkins = sum(1 for m in moods if m.get("source") == "checkin")
        # If the fetch hit its cap, the true count may be higher.
        stats["checkins"] = _capped(checkins, _FETCH_LIMIT) if len(moods) >= _FETCH_LIMIT else str(checkins)
    except Exception:  # noqa: BLE001
        pass
    try:
        logs = conv_db.list_wellness_activity_logs(user, limit=_FETCH_LIMIT)
        stats["activities"] = _capped(len(logs), _FETCH_LIMIT)
    except Exception:  # noqa: BLE001
        pass
    try:
        from backend.streak import get_user_streak
        stats["streak"] = str(get_user_streak(user, conv_db).current_streak)
    except Exception:  # noqa: BLE001
        pass
    return stats


def _render_header_card(user, profile: dict) -> None:
    display_name = profile.get("display_name") or (user.email or "").split("@", 1)[0] or "Sahay AI user"
    lang = _LANG_LABELS.get(profile.get("preferred_language") or "en", "English")
    st.markdown(
        '<div class="sahay-card sahay-profile-header">'
        '<div class="sahay-card-muted-label">MY PROFILE</div>'
        f'<p style="font-size:22px;font-weight:700;margin:2px 0 2px 0;">{_esc(display_name)}</p>'
        f'<div class="sahay-card-caption">{_esc(user.email)}</div>'
        f'<div class="sahay-card-caption">Preferred language: {_esc(lang)}</div>'
        "</div>",
        unsafe_allow_html=True,
    )


def _render_stats(user, profile: dict) -> None:
    stats = _load_stats(user)
    member_since = _format_member_since(profile.get("created_at")) or "—"
    items = (
        ("MEMBER SINCE", member_since),
        ("CURRENT STREAK", f"🔥 {stats['streak']}" if stats["streak"] != "—" else "—"),
        ("CONVERSATIONS", stats["conversations"]),
        ("MOOD CHECK-INS", stats["checkins"]),
        ("WELLNESS ACTIVITIES", stats["activities"]),
    )
    cards = "".join(
        f'<div class="sahay-card"><div class="sahay-card-muted-label">{label}</div>'
        f'<p class="sahay-card-metric">{_esc(value)}</p></div>'
        for label, value in items
    )
    st.markdown(f'{_PROFILE_CSS}<div class="sahay-profile-stats">{cards}</div>', unsafe_allow_html=True)


def _render_quick_links() -> None:
    render_section_header("Quick links")
    links = [(label, key) for label, key in _QUICK_LINKS if key in ALL_PAGE_KEYS]
    for i in range(0, len(links), 2):
        cols = st.columns(2)
        for col, (label, page_key) in zip(cols, links[i:i + 2]):
            with col:
                if st.button(label, key=f"profile_link_{page_key}", use_container_width=True):
                    st.session_state["sahay_page"] = page_key
                    st.rerun()
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)


def _render_demo_mode() -> None:
    st.markdown(
        '<div class="sahay-card sahay-profile-header">'
        '<div class="sahay-card-muted-label">MY PROFILE · DEMO MODE</div>'
        '<p style="font-size:20px;font-weight:700;margin:2px 0 2px 0;">You\'re browsing without an account</p>'
        '<div class="sahay-card-caption">No name, email, or account statistics are shown or stored in Demo Mode.</div>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.text_input("Display name", placeholder="Not available in Demo Mode", disabled=True)
    st.selectbox("Preferred language", ["English", "Hindi", "Hinglish"], disabled=True)
    st.caption("Sign in (see the landing page) to create and edit a real profile.")
    _render_quick_links()


def render() -> None:
    render_page_header("Profile")

    user = auth.get_current_user() if st.session_state.get(
        "sahay_supabase_session"
    ) else None

    if user is None:
        _render_demo_mode()
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

    if st.session_state.pop(_SAVED_FLASH_KEY, False):
        st.success("Profile updated.")

    _render_header_card(user, profile)
    _render_stats(user, profile)
    _render_quick_links()

    render_section_header("Edit profile")
    with st.form("profile_form"):
        display_name = st.text_input(
            "Display name", value=profile.get("display_name") or "", max_chars=60,
        )
        st.text_input(
            "Email address", value=user.email or "", disabled=True,
            help="Your email is your sign-in identity and can't be changed here.",
        )
        languages = ["English", "Hindi", "Hinglish"]
        current_lang_code = profile.get("preferred_language") or "en"
        current_label = _LANG_LABELS.get(current_lang_code, "English")
        preferred_language = st.selectbox(
            "Preferred language", languages,
            index=languages.index(current_label) if current_label in languages else 0,
        )
        submitted = st.form_submit_button("Save changes", type="primary", use_container_width=True)

    if submitted:
        lang_code = {"English": "en", "Hindi": "hi", "Hinglish": "hinglish"}[preferred_language]
        saved = False
        try:
            client = auth.get_client_for_current_user()
            client.table("profiles").update({
                "display_name": display_name.strip(),
                "preferred_language": lang_code,
            }).eq("id", user.id).execute()
            saved = True
        except Exception as exc:  # noqa: BLE001
            st.error("Couldn't save your changes right now. Please try again.")
            st.caption(f"Technical detail (dev preview only): {exc}")
        if saved:
            # Rerun so the sidebar (rendered before this page) shows the new name.
            st.session_state[_SAVED_FLASH_KEY] = True
            st.rerun()

    render_section_header("Account")
    st.caption(f"Signed in as {user.email}")
    if st.button("Log out", key="profile_logout", use_container_width=True):
        # Same sign-out path as the sidebar's Log Out button.
        from components.sidebar import _sign_out
        _sign_out(True)

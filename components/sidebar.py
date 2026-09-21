"""
components/sidebar.py
----------------------
Custom collapsible left navigation for Sahay AI.

Interaction pattern (expand/collapse + active-page highlighting) is adapted
from LearnMate AI's frontend/custom_sidebar.py drawer mechanism — see
/PHASE0_AUDIT.md section B. Visual hierarchy (a bottom profile row, grouped
nav sections) is adapted from the Fitly UX reference — see
/PHASE0_AUDIT.md section D. Branding, copy, and colors are original to
Sahay AI.

PHASE 1 VALIDATION UPDATE: nav groups restructured to MAIN / WELLNESS /
SUPPORT / ACCOUNT per the Phase 1 validation pass (previous grouping used
different labels — this is a content/grouping fix, not a new feature).
Government Services remains its own top-level destination inside SUPPORT,
still never mixed into the chatbot/companion page.

PHASE 2 UPDATE: bottom profile row now reflects real auth state
(backend.auth.AuthUser) when present, falling back to the Demo Mode
status Phase 1 already had. render_sidebar() takes the auth state as a
parameter rather than importing backend.auth itself, keeping this module
free of any Supabase dependency — it only ever displays what
streamlit_app.py already determined.

PHASE 4 (LearnMate-style dashboard shell): the icons-only "density"
collapse from Phase 1 is replaced with a genuine off-canvas drawer —
the same `position: fixed` + `transform: translateX()` mechanism
LearnMate's frontend/custom_sidebar.py uses (see that file's own
docstring for why fixed+transform rather than an animated `width`).
`st.session_state["sahay_sidebar_open"]` is REUSED, not renamed or
replaced — it already meant "is the sidebar's full content visible";
it now drives a full open/closed drawer instead of an icons-only/labels
toggle, which is the same concept taken to its LearnMate-style
conclusion, not a new key. NAV_GROUPS, ALL_PAGE_KEYS, DEFAULT_PAGE, and
this module's public signature (`render_sidebar(authenticated, user) ->
str`) are byte-identical to Phase 1–3 — streamlit_app.py needed no
changes. See PHASE4_DASHBOARD_SHELL_REPORT.md for the full before/after.
"""

from __future__ import annotations

import streamlit as st

from components.theme import sahay_icon_html, COLORS

# ---------------------------------------------------------------------------
# Navigation model (UNCHANGED since Phase 1 validation — content, grouping,
# and page keys are not part of this phase's scope)
# ---------------------------------------------------------------------------
NAV_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    ("Main", [
        ("Overview", "overview"),
        ("Sahay Companion", "companion"),
        ("Mood Check-in", "mood_checkin"),
        ("Wellness Dashboard", "wellness_dashboard"),
    ]),
    ("Wellness", [
        ("Relaxation", "relaxation"),
        ("Mood History", "mood_history"),
        ("Conversations", "conversations"),
        ("Resources", "resources"),
    ]),
    ("Support", [
        ("Government Services", "government_services"),
        ("Human Help", "human_help"),
    ]),
    ("Account", [
        ("Reports", "reports"),
        ("Profile", "profile"),
        ("Privacy", "privacy"),
        ("Settings", "settings"),
    ]),
]

ALL_PAGE_KEYS = [key for _, items in NAV_GROUPS for _, key in items]

DEFAULT_PAGE = "overview"

# ---------------------------------------------------------------------------
# Drawer mechanism constants (Phase 4)
# ---------------------------------------------------------------------------
_DRAWER_WIDTH = "19rem"
_DRAWER_WIDTH_MOBILE = "min(19rem, 85vw)"
_TRANSITION_MS = 260
_TOGGLE_CONTAINER_KEY = "sahay_drawer_toggle"
_TOGGLE_BTN_KEY = "sahay_drawer_toggle_btn"
_BACKDROP_CONTAINER_KEY = "sahay_drawer_backdrop"
_BACKDROP_BTN_KEY = "sahay_drawer_backdrop_btn"


def _init_state() -> None:
    st.session_state.setdefault("sahay_page", DEFAULT_PAGE)
    # Reused key (see module docstring) — default True keeps the drawer
    # open on first load, matching Phase 1–3's prior default behavior.
    st.session_state.setdefault("sahay_sidebar_open", True)


def _render_drawer_shell() -> None:
    """Renders the fixed open/close toggle button, the mobile tap-to-close
    backdrop, and the CSS that turns Streamlit's native sidebar into an
    off-canvas drawer — adapted from LearnMate's
    frontend/custom_sidebar.py `_render_drawer()`. Must be called BEFORE
    `with st.sidebar:` below, for the same reason LearnMate's version
    documents: the toggle/backdrop are independent fixed-position
    elements, not sidebar children, so they don't need to live inside it
    to work — and CSS applied here targets the sidebar from outside it.
    """
    is_open = st.session_state["sahay_sidebar_open"]

    with st.container(key=_TOGGLE_CONTAINER_KEY):
        toggle_clicked = st.button("💙", key=_TOGGLE_BTN_KEY, help="Open / close navigation")

    with st.container(key=_BACKDROP_CONTAINER_KEY):
        backdrop_clicked = st.button("", key=_BACKDROP_BTN_KEY, help="Close navigation")

    if toggle_clicked or (backdrop_clicked and is_open):
        st.session_state["sahay_sidebar_open"] = not st.session_state["sahay_sidebar_open"]
        is_open = st.session_state["sahay_sidebar_open"]

    transform = "translateX(0)" if is_open else "translateX(-100%)"
    backdrop_display = "block" if is_open else "none"
    main_margin = _DRAWER_WIDTH if is_open else "0"

    st.markdown(
        f"""
        <style>
        /* ---- Fixed toggle button: always visible in the same spot,
        regardless of the drawer's open/closed state (same technique as
        components/chatbot_launcher.py's decorative pill, but here the
        REAL interactive button itself is what's fixed — see Phase 1's
        audit note on why that distinction matters). ---- */
        div[class*="st-key-{_TOGGLE_CONTAINER_KEY}"] {{
            position: fixed;
            top: 14px;
            left: 14px;
            z-index: 1000000;
        }}
        div[class*="st-key-{_TOGGLE_BTN_KEY}"] button {{
            width: 42px;
            height: 42px;
            border-radius: 13px;
            padding: 0;
            font-size: 1.05rem;
            box-shadow: var(--sahay-shadow, 0 8px 24px rgba(20,24,33,0.20));
            transition: transform 220ms ease, box-shadow 220ms ease;
        }}
        div[class*="st-key-{_TOGGLE_BTN_KEY}"] button:hover {{
            transform: translateY(-2px);
        }}

        /* ---- The drawer itself: taken out of document flow (fixed),
        full height, slid on/off screen via transform only — see
        LearnMate's custom_sidebar.py docstring for why fixed+transform
        rather than animating width. ---- */
        section[data-testid="stSidebar"] {{
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            height: 100vh !important;
            width: {_DRAWER_WIDTH} !important;
            min-width: {_DRAWER_WIDTH} !important;
            max-width: {_DRAWER_WIDTH} !important;
            z-index: 999998;
            overflow-y: auto !important;
            transform: {transform};
            transition: transform {_TRANSITION_MS}ms ease;
        }}
        @media (max-width: 640px) {{
            section[data-testid="stSidebar"] {{
                width: {_DRAWER_WIDTH_MOBILE} !important;
                min-width: {_DRAWER_WIDTH_MOBILE} !important;
                max-width: {_DRAWER_WIDTH_MOBILE} !important;
            }}
        }}

        /* ---- Desktop: main content margin/width shift in sync with the
        drawer (the sidebar is no longer a flex/grid sibling once fixed,
        so this has to be set explicitly — same reasoning as LearnMate's
        version). Mobile instead overlays (no margin shift; see the
        backdrop below). ---- */
        @media (min-width: 641px) {{
            section[data-testid="stMain"], .main {{
                margin-left: {main_margin} !important;
                width: calc(100% - {main_margin}) !important;
                max-width: calc(100% - {main_margin}) !important;
                transition: margin-left {_TRANSITION_MS}ms ease, width {_TRANSITION_MS}ms ease;
            }}
        }}

        html, body, .stApp {{
            overflow-x: hidden !important;
        }}

        /* ---- Mobile tap-to-close backdrop ---- */
        div[class*="st-key-{_BACKDROP_CONTAINER_KEY}"] {{
            display: none;
        }}
        @media (max-width: 640px) {{
            div[class*="st-key-{_BACKDROP_CONTAINER_KEY}"] {{
                display: {backdrop_display};
                position: fixed;
                inset: 0;
                z-index: 999997;
            }}
            div[class*="st-key-{_BACKDROP_BTN_KEY}"] button {{
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.45) !important;
                border: none !important;
                box-shadow: none !important;
                cursor: pointer;
            }}
        }}

        /* ---- Hide Streamlit's own native collapse control — fully
        replaced by the 💙 toggle button above. Presentational only. ---- */
        div[data-testid="stSidebarCollapseButton"],
        div[data-testid="collapsedControl"] {{
            display: none !important;
        }}

        /* ---- Nav item polish (scoped to this file, not theme.py — the
        primary/secondary st.button styling Phase 2 already added in
        theme.py still applies underneath this). ---- */
        section[data-testid="stSidebar"] .stButton > button {{
            text-align: left !important;
            justify-content: flex-start !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(authenticated: bool = False, user=None) -> str:
    """Render the sidebar drawer and return the currently selected page key.

    `authenticated`/`user` come from streamlit_app.py's auth gate — this
    function never calls backend.auth itself (see module docstring).
    Signature and return value are UNCHANGED from Phase 1–3.
    """
    _init_state()
    _render_drawer_shell()

    with st.sidebar:
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;padding:4px 0 2px 0;'>"
            f"{sahay_icon_html(28)}"
            f"<span class='sahay-display' style='font-size:19px;font-weight:700;'>Sahay AI</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        for group_label, items in NAV_GROUPS:
            st.markdown(
                f"<div class='sahay-sidebar-group-label'>{group_label}</div>",
                unsafe_allow_html=True,
            )
            for label, key in items:
                active = st.session_state["sahay_page"] == key
                if st.button(
                    f"{_icon_for(key)}  {label}",
                    key=f"nav_{key}",
                    use_container_width=True,
                    type="primary" if active else "secondary",
                ):
                    st.session_state["sahay_page"] = key
                    st.rerun()

        # ---- Bottom profile / auth-status row (Fitly-inspired placement,
        # logic unchanged from Phase 1/2 — visual only) ----
        st.markdown("<div class='sahay-sidebar-profile'></div>", unsafe_allow_html=True)
        if authenticated and user is not None:
            label = user.email or "Signed in"
            st.markdown(
                f"**{label}**  \n"
                f"<span style='font-size:12px;color:#6B7280;'>Signed in</span>",
                unsafe_allow_html=True,
            )
            if st.button("Log Out", key="sidebar_signout", use_container_width=True):
                _sign_out(authenticated)
        else:
            st.markdown(
                "**Student**  \n"
                "<span style='font-size:12px;color:#6B7280;'>Demo Mode</span>",
                unsafe_allow_html=True,
            )
            if st.button("Exit Demo Mode", key="sidebar_exit_demo", use_container_width=True):
                _sign_out(authenticated)
            st.caption("Sign in for a real, private account.")

    return st.session_state["sahay_page"]


def _sign_out(authenticated: bool) -> None:
    if authenticated:
        from backend import auth
        auth.sign_out()
    st.session_state["sahay_view"] = "landing"
    st.session_state["sahay_demo_mode"] = False
    st.session_state["sahay_page"] = DEFAULT_PAGE
    st.rerun()


def _icon_for(page_key: str) -> str:
    icons = {
        "overview": "🏠",
        "companion": "💬",
        "mood_checkin": "🙂",
        "relaxation": "🧘",
        "wellness_dashboard": "📊",
        "resources": "📚",
        "human_help": "🤝",
        "government_services": "🇮🇳",
        "conversations": "🗂️",
        "mood_history": "📈",
        "reports": "📄",
        "profile": "👤",
        "privacy": "🔒",
        "settings": "⚙️",
    }
    return icons.get(page_key, "•")

"""
admin/theme.py
-----------------
Admin Panel visual layer (UI/UX only).

Presentation helpers for admin/login.py and admin/shell.py. Nothing in
this module touches authentication, session handling, database access,
or any admin_data/admin_auth function — it only emits CSS.

It deliberately REUSES Sahay's existing design system instead of
defining a second theme: colors come from components.theme.COLORS, the
dark/light choice comes from the same st.session_state["sahay_dark_mode"]
flag components.theme.inject_css() already reads, and the gradient,
border, shadow, and radius come from the --sahay-* CSS variables that
inject_css() already defines on :root. inject_css() itself is untouched
and still runs first (streamlit_app.py, module level), so every generic
button/input/label rule it defines keeps applying underneath.

These rules are only ever emitted from the ?admin=1 flow (the student
app never imports this module), so they cannot affect any student page.
"""

from __future__ import annotations

import streamlit as st

from components.theme import COLORS

# Same drawer geometry/timing as the student sidebar (components/sidebar.py)
# so the two feel like one product. Duplicated as plain constants rather
# than imported: sidebar.py's are private, and that file is left untouched.
DRAWER_WIDTH = "19rem"
DRAWER_WIDTH_MOBILE = "min(19rem, 85vw)"
TRANSITION_MS = 260

# Widget keys for the admin drawer's fixed controls. Chosen so none is a
# substring of another (the CSS below matches on class*="st-key-<key>").
TOGGLE_BOX_KEY = "admin_drawer_box"
TOGGLE_BTN_KEY = "admin_drawer_toggle_btn"
BACKDROP_BOX_KEY = "admin_drawer_backdrop_box"
BACKDROP_BTN_KEY = "admin_drawer_backdrop_btn"


def _tokens() -> dict[str, str]:
    dark = st.session_state.get("sahay_dark_mode", True)
    return {
        "card": COLORS["card_dark"] if dark else COLORS["card_light"],
        "text": COLORS["text_dark"] if dark else COLORS["text_light"],
        "muted": COLORS["muted_dark"] if dark else COLORS["muted_light"],
    }


def inject_admin_css(login: bool = False) -> None:
    """Shared Admin Panel styling. `login=True` narrows and centers the
    page for the sign-in card; the authenticated shell uses a wider
    (but still capped) content column."""
    t = _tokens()
    max_width = "560px" if login else "1200px"
    accent = COLORS["soft_teal"]

    st.markdown(
        f"""
        <style>
        html, body, .stApp {{
            overflow-x: hidden !important;
        }}

        /* ---- Page column: centered, capped, room for the fixed toggle ---- */
        [data-testid="stMainBlockContainer"], .block-container {{
            max-width: {max_width} !important;
            margin-left: auto !important;
            margin-right: auto !important;
            padding-top: 3.5rem !important;
            padding-bottom: 3rem !important;
        }}

        /* ---- "ADMIN PANEL" badge + identity line ---- */
        .sahay-admin-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: {accent};
            background: {accent}1F;
            border: 1px solid {accent}55;
            padding: 4px 12px;
            border-radius: 999px;
        }}
        .sahay-admin-topline {{
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            margin: 0 0 14px 0;
        }}
        .sahay-admin-who {{
            font-size: 12.5px;
            color: {t['muted']};
            overflow-wrap: anywhere;
        }}

        /* ---- Hero (login) ---- */
        .sahay-admin-hero {{
            background: linear-gradient(
                135deg,
                rgba(166, 25, 60, 0.30) 0%,
                rgba(193, 82, 119, 0.14) 55%,
                rgba(217, 119, 87, 0.12) 100%
            );
            border: 1px solid var(--sahay-border);
            border-radius: 22px;
            padding: 26px 26px 24px 26px;
            box-shadow: var(--sahay-shadow);
            margin-bottom: 18px;
        }}
        .sahay-admin-hero-title {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 16px 0 8px 0;
            font-family: 'Space Grotesk', sans-serif;
            font-size: clamp(1.4rem, 5.2vw, 2rem);
            font-weight: 700;
            line-height: 1.15;
            letter-spacing: -0.01em;
        }}
        /* The shield emoji is kept OUTSIDE the gradient-clipped span:
           color-emoji glyphs can disappear under a transparent text fill. */
        .sahay-admin-grad {{
            background: var(--sahay-gradient);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            -webkit-text-fill-color: transparent;
        }}
        .sahay-admin-hero-sub {{
            font-size: 14px;
            color: {t['muted']};
            line-height: 1.5;
        }}

        /* ---- Sign-in form card ---- */
        [data-testid="stForm"] {{
            background: {t['card']};
            border: 1px solid var(--sahay-border) !important;
            border-radius: 18px !important;
            padding: 22px 22px 18px 22px !important;
            box-shadow: var(--sahay-shadow);
        }}
        [data-testid="stForm"] input:focus {{
            border-color: {COLORS['lavender']} !important;
            box-shadow: 0 0 0 1px {COLORS['lavender']} !important;
        }}
        [data-testid="stFormSubmitButton"] button {{
            background: var(--sahay-gradient) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 0.6rem 1rem !important;
            font-weight: 600 !important;
            box-shadow: 0 6px 18px rgba(166, 25, 60, 0.28);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }}
        [data-testid="stFormSubmitButton"] button:hover {{
            transform: translateY(-1px);
            box-shadow: 0 10px 24px rgba(166, 25, 60, 0.38);
        }}

        /* ---- "Back to Sahay AI" link + divider ---- */
        .sahay-admin-divider {{
            border: none;
            border-top: 1px solid var(--sahay-border);
            margin: 22px 0 14px 0;
        }}
        .sahay-admin-back {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 9px 16px;
            border-radius: 12px;
            background: {t['card']};
            border: 1px solid var(--sahay-border);
            color: {t['text']} !important;
            font-size: 13.5px;
            font-weight: 600;
            text-decoration: none !important;
            transition: border-color 0.15s ease, color 0.15s ease;
        }}
        .sahay-admin-back:hover {{
            border-color: {COLORS['deep_blue']};
            color: {COLORS['deep_blue']} !important;
        }}

        /* ---- Existing admin views: presentation only ---- */
        [data-testid="stMetric"] {{
            background: {t['card']};
            border: 1px solid var(--sahay-border);
            border-radius: 16px;
            padding: 14px 16px;
            box-shadow: var(--sahay-shadow);
        }}
        [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p {{
            color: {t['muted']} !important;
            font-size: 12px !important;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }}
        [data-testid="stMetricValue"] {{
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 700;
        }}
        [data-testid="stVegaLiteChart"], [data-testid="stArrowVegaLiteChart"] {{
            background: {t['card']};
            border: 1px solid var(--sahay-border);
            border-radius: 16px;
            padding: 8px;
            overflow: hidden;
        }}
        [data-testid="stVerticalBlockBorderWrapper"] {{
            border-radius: 16px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_admin_drawer_css(is_open: bool) -> None:
    """Off-canvas drawer for the admin sidebar — the same fixed +
    translateX technique as components/sidebar.py, minus the parts that
    only exist for the student app (the chat_input `stBottom` bar). On
    desktop the main column shifts with the drawer; on mobile the drawer
    overlays and a tap-to-close backdrop is shown."""
    transform = "translateX(0)" if is_open else "translateX(-100%)"
    backdrop_display = "block" if is_open else "none"
    main_margin = DRAWER_WIDTH if is_open else "0"

    st.markdown(
        f"""
        <style>
        div[class*="st-key-{TOGGLE_BOX_KEY}"] {{
            position: fixed;
            top: 14px;
            left: 14px;
            z-index: 1000000;
        }}
        div[class*="st-key-{TOGGLE_BTN_KEY}"] button {{
            width: 42px;
            height: 42px;
            border-radius: 13px;
            padding: 0;
            font-size: 1.05rem;
            box-shadow: var(--sahay-shadow);
            transition: transform 220ms ease, box-shadow 220ms ease;
        }}
        div[class*="st-key-{TOGGLE_BTN_KEY}"] button:hover {{
            transform: translateY(-2px);
        }}

        section[data-testid="stSidebar"] {{
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            height: 100vh !important;
            width: {DRAWER_WIDTH} !important;
            min-width: {DRAWER_WIDTH} !important;
            max-width: {DRAWER_WIDTH} !important;
            z-index: 999998;
            overflow-y: auto !important;
            transform: {transform};
            transition: transform {TRANSITION_MS}ms ease;
        }}
        @media (max-width: 640px) {{
            section[data-testid="stSidebar"] {{
                width: {DRAWER_WIDTH_MOBILE} !important;
                min-width: {DRAWER_WIDTH_MOBILE} !important;
                max-width: {DRAWER_WIDTH_MOBILE} !important;
            }}
        }}

        /* Desktop: shift the main column in step with the drawer so
           nothing is cropped underneath it. */
        @media (min-width: 641px) {{
            section[data-testid="stMain"], .main {{
                margin-left: {main_margin} !important;
                width: calc(100% - {main_margin}) !important;
                max-width: calc(100% - {main_margin}) !important;
                transition: margin-left {TRANSITION_MS}ms ease, width {TRANSITION_MS}ms ease;
            }}
        }}

        /* Mobile: overlay + tap-to-close backdrop (no margin shift). */
        div[class*="st-key-{BACKDROP_BOX_KEY}"] {{
            display: none;
        }}
        @media (max-width: 640px) {{
            div[class*="st-key-{BACKDROP_BOX_KEY}"] {{
                display: {backdrop_display};
                position: fixed;
                inset: 0;
                z-index: 999997;
            }}
            div[class*="st-key-{BACKDROP_BTN_KEY}"] button {{
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.45) !important;
                border: none !important;
                box-shadow: none !important;
                cursor: pointer;
            }}
        }}

        /* Replaced by the 🛡️ toggle above. */
        div[data-testid="stSidebarCollapseButton"],
        div[data-testid="collapsedControl"] {{
            display: none !important;
        }}

        section[data-testid="stSidebar"] .stButton > button {{
            text-align: left !important;
            justify-content: flex-start !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

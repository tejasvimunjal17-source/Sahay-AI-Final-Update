"""
components/theme.py
--------------------
Design tokens + CSS injection for Sahay AI.

PHASE (red-based premium redesign, approved): the palette moved from the
original blue/teal/lavender direction to a deep-red/crimson-led identity
— deep crimson (primary), dusty rose (secondary/complementary), warm
terracotta (tertiary accent) — per your explicit request for a
LearnMate-quality *visual finish* with a distinctly Sahay-own red
identity, not LearnMate's colors. Dictionary KEYS are unchanged
(`deep_blue`, `soft_teal`, `lavender`, etc.) — only their VALUES moved,
per your instruction to avoid restructuring; every file that reads
`COLORS["deep_blue"]` etc. keeps working unmodified. `safety_amber`/
`safety_red` — the two colors reserved for safety-escalation UI — were
deliberately left untouched, so the brand's new red identity and the
app's actual crisis/error messaging (`st.error`, native Streamlit
colors) remain visually distinguishable from each other.

PHASE 2 (LearnMate-inspired design system): token *values* and the CSS
they feed were tuned toward LearnMate AI's visual language — deep-navy
background, elevated dark cards, rounded/shadowed surfaces, a
violet-leaning secondary accent, restrained borders — extracted from
LearnMate's frontend/styles.py (`_theme_vars`, `--radius`, `--shadow`,
the `.stButton > button` / input radius rules, and the `.glass-card`
elevation treatment). No LearnMate color hex values, copy, or branding
were copied in; Sahay's own three brand hues (deep_blue, soft_teal,
lavender — all pre-existing in this file) are what get used to fill that
visual language, so `lavender`, defined here since Phase 1 but never
previously referenced in any CSS rule, now does double duty as Sahay's
own violet/blue-adjacent accent alongside deep_blue and soft_teal. Card
border-radius (18px) already matched LearnMate's `--radius` before this
change; button/input radius (12px / 10px) are newly aligned to
LearnMate's values here. Nothing outside this file changed — see
PHASE2_THEME_REPORT.md for the full before/after token table.
"""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
COLORS = {
    # ---- Sahay brand hues (KEYS unchanged; VALUES updated to the
    # approved red-based identity — deep crimson primary, dusty-rose
    # secondary, warm terracotta tertiary accent) ----
    "deep_blue": "#A6193C",
    "soft_teal": "#D97757",
    "lavender": "#C15277",
    "white": "#FFFFFF",
    "dark_slate": "#1E2430",
    # ---- Base surfaces ----
    # bg_light warmed very slightly (near-white, not cool-white) to sit
    # cohesively with the new red identity; bg_dark shifted from navy to
    # a warm, near-black plum so dark mode reads as a premium dark theme
    # built around the same hue family as the brand, not a leftover blue.
    "bg_light": "#FDF8F7",
    "bg_dark": "#1A1013",
    # A distinct *elevated* surface, one step lighter than bg_dark, so
    # cards/sidebar visibly sit "above" the page background instead of
    # blending into it.
    "bg_elevated_light": "#FFFFFF",
    "bg_elevated_dark": "#241820",
    "card_light": "#FFFFFF",
    "card_dark": "#241820",
    "text_light": "#1E2430",
    "text_dark": "#EDEEF5",
    "muted_light": "#6B7280",
    "muted_dark": "#9CA3AF",
    # Restrained card/sidebar border tones (unchanged — neutral borders
    # read fine against either hue family and didn't need to move).
    "border_light": "rgba(20, 24, 33, 0.08)",
    "border_dark": "rgba(255, 255, 255, 0.09)",
    # Elevation shadows (unchanged — shadows are black-based regardless
    # of brand hue).
    "shadow_light": "0 8px 24px rgba(30, 32, 70, 0.08)",
    "shadow_dark": "0 8px 30px rgba(0, 0, 0, 0.35)",
    # Reserved strictly for safety-escalation UI — deliberately NOT
    # changed by the red-brand redesign above, so a real warning still
    # reads as visually distinct from ordinary branding.
    "safety_amber": "#B45309",
    "safety_red": "#B3261E",
}

ICON_PATH = Path(__file__).parent.parent / "assets" / "sahay_icon.svg"


def _icon_b64() -> str:
    return base64.b64encode(ICON_PATH.read_bytes()).decode("utf-8")


def sahay_icon_html(size_px: int = 28) -> str:
    """The single, consistent Sahay glyph — heart-in-speech-bubble.

    Use this everywhere the companion needs a visual identity (launcher,
    sidebar wordmark, chat header, avatar, empty/loading states) instead of
    ad-hoc emoji, so the icon stays a single recognizable mark per the
    master spec's branding requirement.
    """
    b64 = _icon_b64()
    return (
        f'<img src="data:image/svg+xml;base64,{b64}" '
        f'width="{size_px}" height="{size_px}" '
        f'style="vertical-align:middle;" alt="Sahay" />'
    )


def inject_css(dark_mode: bool = False) -> None:
    bg = COLORS["bg_dark"] if dark_mode else COLORS["bg_light"]
    bg_elevated = COLORS["bg_elevated_dark"] if dark_mode else COLORS["bg_elevated_light"]
    card = COLORS["card_dark"] if dark_mode else COLORS["card_light"]
    text = COLORS["text_dark"] if dark_mode else COLORS["text_light"]
    muted = COLORS["muted_dark"] if dark_mode else COLORS["muted_light"]
    border = COLORS["border_dark"] if dark_mode else COLORS["border_light"]
    shadow = COLORS["shadow_dark"] if dark_mode else COLORS["shadow_light"]
    # Sahay's own three-hue gradient (blue -> lavender -> teal), used for
    # the accent card and for interactive-element accents below — no new
    # brand colors, just the existing palette put to fuller use.
    gradient = (
        f"linear-gradient(120deg, {COLORS['deep_blue']} 0%, "
        f"{COLORS['lavender']} 55%, {COLORS['soft_teal']} 100%)"
    )

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

        :root {{
            --sahay-radius: 18px;
            --sahay-radius-sm: 12px;
            --sahay-radius-input: 10px;
            --sahay-shadow: {shadow};
            --sahay-border: {border};
            --sahay-gradient: {gradient};
        }}

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}
        h1, h2, h3, .sahay-display {{
            font-family: 'Space Grotesk', sans-serif;
            letter-spacing: -0.01em;
        }}

        .stApp {{
            background-color: {bg};
            color: {text};
        }}

        /* ---- Cards ----
           Elevated one step above the page background (bg_elevated vs.
           bg), with a restrained border and a softer, wider shadow than
           before — the "polished SaaS card" treatment, still Sahay's own
           card/card-dark colors, not LearnMate's. */
        .sahay-card {{
            background: {card};
            border-radius: var(--sahay-radius);
            padding: 22px 24px;
            box-shadow: var(--sahay-shadow);
            margin-bottom: 16px;
            border: 1px solid var(--sahay-border);
        }}
        .sahay-card-muted-label {{
            font-size: 12px;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: {muted};
            margin-bottom: 6px;
        }}
        .sahay-card-metric {{
            font-size: 30px;
            font-weight: 700;
            font-family: 'Space Grotesk', sans-serif;
            margin: 0;
        }}
        .sahay-card-caption {{
            font-size: 13px;
            color: {muted};
            margin-top: 4px;
        }}

        /* ---- Companion accent card (deliberately dark, like the
               reference app's contrast card, to signal "this is Sahay") ----
           Now a three-stop blue -> lavender -> teal gradient instead of a
           two-stop blue -> teal one, using the same brand hues, for a
           softer, less flat aurora-style transition. */
        .sahay-accent-card {{
            background: var(--sahay-gradient);
            color: #FFFFFF;
            border-radius: var(--sahay-radius);
            padding: 22px 24px;
            margin-bottom: 16px;
            box-shadow: var(--sahay-shadow);
        }}
        .sahay-accent-card .sahay-card-caption {{
            color: rgba(255,255,255,0.75);
        }}

        /* ---- Safety / disclaimer banner (semantics/color meaning
               unchanged — still teal-bordered, still uses soft_teal) ---- */
        .sahay-safety-note {{
            font-size: 12.5px;
            color: {muted};
            border-left: 3px solid {COLORS['soft_teal']};
            padding: 8px 12px;
            background: rgba(63, 175, 160, 0.08);
            border-radius: 6px;
            margin: 10px 0 18px 0;
        }}

        /* ---- Floating chatbot launcher ----
           Positioning, size, and behavior are UNCHANGED in this phase
           (that fix is scoped to a later Floating Chatbot phase) — only
           the shadow token below was aligned to the new shared --sahay-shadow
           for visual consistency with the rest of the redesigned surfaces. */
        .sahay-launcher {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 999;
            background: {COLORS['dark_slate']};
            color: #FFFFFF;
            border-radius: 999px;
            padding: 12px 20px 12px 14px;
            display: flex;
            align-items: center;
            gap: 10px;
            box-shadow: 0 8px 24px rgba(20,24,33,0.25);
            cursor: pointer;
        }}
        .sahay-launcher-title {{
            font-size: 13.5px;
            font-weight: 600;
            line-height: 1.1;
        }}
        .sahay-launcher-subtitle {{
            font-size: 11px;
            color: rgba(255,255,255,0.65);
            line-height: 1.1;
        }}

        /* ---- Sidebar ----
           Background promoted to the new elevated surface (was the same
           flat "card" color used everywhere) so the sidebar reads as its
           own layer, matching LearnMate's elevated-panel sidebar look.
           Structure/nav markup itself is untouched (components/sidebar.py
           not modified this phase). ---- */
        section[data-testid="stSidebar"] {{
            background-color: {bg_elevated};
            border-right: 1px solid var(--sahay-border);
        }}
        .sahay-sidebar-group-label {{
            font-size: 11px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: {muted};
            margin: 18px 0 4px 8px;
        }}
        .sahay-sidebar-profile {{
            border-top: 1px solid var(--sahay-border);
            padding-top: 12px;
            margin-top: 12px;
            font-size: 13px;
        }}

        /* ---- Buttons / inputs ----
           Generic Streamlit-widget polish (radius, restrained shadow,
           hover lift) so every existing st.button/text input across every
           existing page picks up the new look automatically, with no
           changes to any page/component file. Radius values (12px
           buttons, 10px inputs) match LearnMate's extracted tokens; the
           button gradient reuses Sahay's own --sahay-gradient, not
           LearnMate's violet. */
        .stButton > button, .stDownloadButton > button, .stLinkButton > a {{
            border-radius: var(--sahay-radius-sm) !important;
            border: none !important;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }}
        .stButton > button[kind="primary"] {{
            background: var(--sahay-gradient) !important;
            color: #FFFFFF !important;
            box-shadow: 0 6px 18px rgba(47, 93, 138, 0.28);
        }}
        .stButton > button[kind="primary"]:hover {{
            box-shadow: 0 10px 24px rgba(47, 93, 138, 0.36);
            transform: translateY(-1px);
        }}
        .stTextInput input, .stNumberInput input, .stTextArea textarea,
        .stDateInput input, .stSelectbox > div > div {{
            border-radius: var(--sahay-radius-input) !important;
        }}

        /* ---- PHASE (device-theme independence, approved) ----
           Explicitly styles every native Streamlit widget class that
           theme.py previously left unstyled (default/secondary buttons,
           text/number/password inputs, textareas, select boxes, tabs,
           labels, placeholder text, and the password show/hide icon).
           Without this block, those elements fell back to Streamlit's
           OWN native theme, which — with no [theme] section in
           .streamlit/config.toml — auto-follows the browser/OS
           `prefers-color-scheme`. That's what caused low-contrast
           "black box" buttons/inputs when a phone was in Dark Mode while
           Sahay's own light mode was selected (or vice versa). Every
           rule below reuses the SAME `bg`/`card`/`text`/`muted`/`border`
           variables already computed above from `st.session_state
           ["sahay_dark_mode"]` — so Sahay's own toggle becomes the only
           thing that can change these colors, regardless of device
           theme. */
        .stButton > button:not([kind="primary"]),
        .stDownloadButton > button {{
            background: {card} !important;
            color: {text} !important;
            border: 1px solid var(--sahay-border) !important;
        }}
        .stButton > button:not([kind="primary"]):hover,
        .stDownloadButton > button:hover {{
            border-color: {COLORS['deep_blue']} !important;
            color: {COLORS['deep_blue']} !important;
        }}
        .stButton > button:disabled {{
            background: {card} !important;
            color: {muted} !important;
            opacity: 0.7;
        }}
        .stTextInput input, .stNumberInput input, .stTextArea textarea,
        .stDateInput input {{
            background: {card} !important;
            color: {text} !important;
            border: 1px solid var(--sahay-border) !important;
        }}
        .stTextInput input::placeholder, .stTextArea textarea::placeholder {{
            color: {muted} !important;
            opacity: 1;
        }}
        /* Password show/hide "eye" icon — Streamlit renders this as a
           button with an inline svg inside the input's wrapper; forcing
           the icon's own color (not just the input's) keeps it visible
           in both modes regardless of device theme. */
        .stTextInput button svg {{
            fill: {muted} !important;
        }}
        .stSelectbox > div > div, .stMultiSelect > div > div {{
            background: {card} !important;
            color: {text} !important;
            border: 1px solid var(--sahay-border) !important;
        }}
        /* Widget labels (e.g. "Email", "Password") and general markdown
           text inside forms/widgets. */
        .stTextInput label, .stTextArea label, .stSelectbox label,
        .stNumberInput label, .stDateInput label, .stRadio label,
        .stCheckbox label, .stSlider label {{
            color: {text} !important;
        }}
        /* Tabs (Log In / Sign Up / Forgot Password) */
        .stTabs [data-baseweb="tab-list"] {{
            background: transparent !important;
            border-bottom: 1px solid var(--sahay-border) !important;
        }}
        .stTabs [data-baseweb="tab"] {{
            color: {muted} !important;
        }}
        .stTabs [aria-selected="true"] {{
            color: {COLORS['deep_blue']} !important;
        }}

        /* Hide default Streamlit chrome that clashes with the custom shell */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        /* PHASE (native header strip fix, approved): toolbarMode="minimal" in
           .streamlit/config.toml already suppresses the native toolbar's
           contents (hamburger menu, Deploy button, etc.) — this rule
           additionally collapses the thin header BAR ELEMENT ITSELF, which
           Streamlit still reserves even in minimal mode, along with the
           blank vertical space it leaves. Scoped to exactly one selector,
           `header[data-testid="stHeader"]` — Streamlit's own native header,
           not any Sahay-authored element — so it cannot affect
           components/sidebar.py's drawer, components/topbar.py's page
           header, or any page content. This does NOT and cannot remove any
           chrome a hosting platform (e.g. Streamlit Community Cloud) renders
           outside the application's own DOM. */
        header[data-testid="stHeader"] {{
            height: 0rem;
            visibility: hidden;
        }}

        /* ---- Responsive adjustments ----
           Streamlit's own layout already stacks st.columns() vertically
           below ~640px viewport width and collapses the sidebar into an
           off-canvas drawer on narrow screens; these rules only tighten
           spacing/sizing on top of that built-in behavior so nothing
           overflows horizontally on tablet/mobile widths. */
        @media (max-width: 768px) {{
            .sahay-card, .sahay-accent-card {{
                padding: 16px 16px;
            }}
            .sahay-launcher {{
                bottom: 14px;
                right: 14px;
                padding: 10px 14px 10px 10px;
            }}
            .sahay-launcher-subtitle {{
                display: none;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

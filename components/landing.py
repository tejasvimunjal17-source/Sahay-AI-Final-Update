"""
components/landing.py
------------------------
Pre-authentication landing page.

PHASE 2 UPDATE: real email/password sign-up, log-in, and forgot-password
forms now call backend/auth.py. "Continue with Google" is wired to a real
Supabase/Google OAuth redirect when GOOGLE_OAUTH_CONFIG is configured —
see PHASE2_IMPLEMENTATION_REPORT.md for what has and hasn't been
live-tested. When OAuth isn't configured (the default — no secrets set),
the button still shows the same friendly "not available yet" notice
Phase 1 had, rather than erroring.

"Continue in Demo Mode" is KEPT, per your Phase 2 instructions, as an
explicit, clearly-labeled, no-account preview path — see
streamlit_app.py's auth gate and components/sidebar.py for how it stays
visually and functionally separate from a real signed-in session (never
touches Supabase, never reads/writes profiles).

PHASE 3 (LearnMate-style landing redesign): visual structure only —
fixed top nav, an elevated gradient hero card, equal-height hover-lift
feature cards, and a short closing section — adapted from LearnMate AI's
frontend/landing.py + the "Landing Page" section of frontend/styles.py
(see PHASE3_LANDING_REPORT.md for the full before/after + section
mapping). No authentication call, session-state write, CTA destination,
FEATURES content, or safety-notice wording changed — every function
below that touches backend.auth or st.session_state is byte-identical
to Phase 2 except for the HTML/CSS it's wrapped in. Design lineage note
above (Fitly-inspired step-indicator hero) is superseded by this phase's
LearnMate-inspired hero treatment; kept here for history.

No Admin Panel entry was added to this page: Sahay's current admin
access is the unlinked `?admin=1` query-param route only (see
admin/login.py) — LearnMate's landing page links to its own equivalent,
but Sahay's landing page never has, so none was invented here per the
Phase 3 instruction not to add functionality that doesn't already exist.
"""

from __future__ import annotations

import base64

import streamlit as st

from components.theme import sahay_icon_html, COLORS
from config import GOOGLE_OAUTH_CONFIG, SUPABASE_USER_CONFIG

# ---------------------------------------------------------------------------
# Google "G" icon (approved, Change 4) — standard, publicly-documented
# four-color Google logomark, embedded as a data-URI background-image via
# CSS (see `.sahay-google-icon-var` rule below), exactly the same
# base64-data-URI technique components/theme.py's own sahay_icon_html()
# already uses for the Sahay wordmark. Rendered as a background-image
# (not inline <svg>), so it cannot be recolored by any CSS/dark-mode rule
# and stays visible in both Sahay Light and Dark Mode.
# ---------------------------------------------------------------------------
_GOOGLE_ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 18 18" width="18" height="18">
<path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.874 2.684-6.615z"/>
<path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332C2.438 15.983 5.482 18 9 18z"/>
<path fill="#FBBC05" d="M3.964 10.71c-.18-.54-.282-1.117-.282-1.71s.102-1.17.282-1.71V4.958H.957C.348 6.173 0 7.548 0 9s.348 2.827.957 4.042l3.007-2.332z"/>
<path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0 5.482 0 2.438 2.017.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z"/>
</svg>"""


def _google_icon_css() -> str:
    """A tiny, separate CSS injection defining the one `--sahay-google-icon`
    variable `.sahay-google-icon` rules (in _LANDING_CSS) consume. Kept
    separate from the big static _LANDING_CSS constant so that constant
    doesn't need converting to an f-string (which would require escaping
    every one of its many literal `{`/`}` CSS braces) just for this one
    dynamic value."""
    b64 = base64.b64encode(_GOOGLE_ICON_SVG.encode("utf-8")).decode("utf-8")
    return f'<style>:root {{ --sahay-google-icon: url("data:image/svg+xml;base64,{b64}"); }}</style>'

FEATURES = [
    ("💬", "Talk it through", "A calm, judgment-free space to reflect on how your day or week is going."),
    ("🙂", "Check in with yourself", "A quick, optional mood check-in — never mandatory, never a diagnosis."),
    ("🧘", "Reset when you need to", "Short breathing, grounding, and study-break exercises you can use anytime."),
    ("🤝", "Find real support", "Clear pointers to campus, professional, and government resources when you want more than a chat."),
]

# ---------------------------------------------------------------------------
# Landing-page-scoped CSS (Phase 3).
#
# Deliberately self-contained here rather than added to components/theme.py
# — matches the pattern LearnMate itself uses for one-surface styling (e.g.
# frontend/chatbot.py's own _CHAT_CSS constant), and keeps this phase's
# change confined to this one file as instructed. Reuses the exact tokens
# Phase 2 already put in components/theme.py's :root block
# (--sahay-radius, --sahay-shadow, --sahay-border, --sahay-gradient) rather
# than inventing new ones — Phase 2's inject_css() already ran by the time
# this page renders (streamlit_app.py calls it before render_landing_page),
# so those variables are already defined on :root.
# ---------------------------------------------------------------------------
_LANDING_CSS = """
<style>
/* ---------- Fixed top navigation ---------- */
.sahay-landing-topnav {
    position: fixed;
    top: 0; left: 0; right: 0;
    z-index: 999;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.85rem 2rem;
    background: color-mix(in srgb, var(--sahay-border) 0%, transparent);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--sahay-border);
}
.sahay-landing-topnav-spacer { height: 60px; }

/* ---------- Admin Panel link (approved) ---------- */
.sahay-admin-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border-radius: 999px;
    background: var(--sahay-gradient);
    color: #FFFFFF !important;
    font-size: 13px;
    font-weight: 600;
    text-decoration: none !important;
    box-shadow: 0 4px 14px rgba(166, 25, 60, 0.28);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    white-space: nowrap;
}
.sahay-admin-link:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 20px rgba(166, 25, 60, 0.36);
}

/* ---------- Hero (fixed container — see _hero()) ----------
   Previously this background/radius/shadow was applied to a
   `st.markdown('<div>...')`/`st.markdown('</div>')` pair that Streamlit
   renders as two SEPARATE, unnested blocks — leaving an empty styled
   div (the "blank rectangle") and the real content unstyled beneath it.
   Fixed by moving these rules onto the auto-generated class Streamlit
   gives a `st.container(key="sahay_landing_hero")` — a real DOM
   ancestor of everything rendered inside that `with` block, so the
   background now actually wraps the headline/subtitle/accent-card. */
div[class*="st-key-sahay_landing_hero"] {
    position: relative;
    border-radius: var(--sahay-radius);
    padding: 2.4rem 2.2rem;
    background:
        radial-gradient(120% 160% at 0% 0%, rgba(166,25,60,0.14), transparent 60%),
        radial-gradient(120% 160% at 100% 0%, rgba(217,119,87,0.12), transparent 55%);
    border: 1px solid var(--sahay-border);
    box-shadow: var(--sahay-shadow);
    margin-bottom: 1.6rem;
    overflow: hidden;
}
.sahay-landing-hero h1 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.2rem;
    line-height: 1.18;
    margin: 0 0 0.7rem 0;
}
.sahay-landing-hero-sub {
    font-size: 16px;
    line-height: 1.65;
    max-width: 520px;
    margin-top: 6px;
}

/* ---------- Floating wellness glyphs (approved, Change 5) ----------
   Decorative only — position:absolute + pointer-events:none so they
   never intercept clicks or sit above interactive content (z-index: 0,
   behind the headline/columns which render afterward in normal flow).
   Animation is a slow, small vertical drift; disabled entirely for
   anyone with prefers-reduced-motion set. */
.sahay-hero-glyph {
    position: absolute;
    z-index: 0;
    opacity: 0.16;
    font-size: 28px;
    pointer-events: none;
    animation: sahay-float 7s ease-in-out infinite;
}
.sahay-hero-glyph-1 { top: 8%;  left: 4%;  animation-delay: 0s; }
.sahay-hero-glyph-2 { top: 65%; left: 8%;  font-size: 22px; animation-delay: 1.2s; }
.sahay-hero-glyph-3 { top: 15%; left: 92%; font-size: 24px; animation-delay: 0.6s; }
.sahay-hero-glyph-4 { top: 55%; left: 95%; animation-delay: 2s; }
.sahay-hero-glyph-5 { top: 85%; left: 45%; font-size: 20px; animation-delay: 1.6s; }
@keyframes sahay-float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-8px); }
}
@media (prefers-reduced-motion: reduce) {
    .sahay-hero-glyph { animation: none; }
}

/* ---------- "Check In -> Reflect -> Relax -> Get Support" strip ---------- */
.sahay-hero-journey {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 1.6rem;
    padding-top: 1.1rem;
    border-top: 1px solid var(--sahay-border);
    font-size: 12.5px;
}
.sahay-hero-journey-step {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    color: var(--sahay-muted, inherit);
    opacity: 0.85;
}
.sahay-hero-journey-arrow {
    opacity: 0.45;
    margin: 0 2px;
}
@media (max-width: 768px) {
    .sahay-hero-journey { font-size: 11.5px; gap: 4px; }
    .sahay-hero-glyph { display: none; }
}

/* ---------- Google button icon (approved, Change 4) ----------
   Targets the Streamlit-auto-generated `st-key-landing_google*` class
   shared by all three Google button/link variants (normal, configured
   link, disabled-error) — a substring match, so one rule covers all
   three without touching their Python call sites' logic. The emoji
   prefix was removed from each label; this ::before supplies the
   multicolor "G" as a background image instead, immune to any text/
   icon-color CSS since it's a background-image, not a glyph. */
div[class*="st-key-landing_google"] button,
div[class*="st-key-landing_google"] a {
    display: flex !important;
    align-items: center;
    justify-content: center;
    gap: 10px;
}
div[class*="st-key-landing_google"] button::before,
div[class*="st-key-landing_google"] a::before {
    content: "";
    display: inline-block;
    width: 18px;
    height: 18px;
    background-image: var(--sahay-google-icon);
    background-size: contain;
    background-repeat: no-repeat;
    background-position: center;
    flex-shrink: 0;
}

/* ---------- Section titles ---------- */
.sahay-landing-section-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.35rem;
    text-align: center;
    margin: 1.4rem 0 1.1rem 0;
}

/* ---------- Feature cards ----------
   Equal-height, hover-lift cards — same technique LearnMate's
   .lm-feature-card uses (stretch the Streamlit column + every wrapper
   div between it and the card to flex:1/height:100%), applied to
   Sahay's existing .sahay-card class rather than a new one. */
div[data-testid="column"]:has(.sahay-landing-feature) {
    display: flex;
}
div[data-testid="column"]:has(.sahay-landing-feature) > div,
div[data-testid="column"]:has(.sahay-landing-feature) [data-testid="stVerticalBlock"],
div[data-testid="column"]:has(.sahay-landing-feature) [data-testid="element-container"],
div[data-testid="column"]:has(.sahay-landing-feature) [data-testid="stMarkdown"],
div[data-testid="column"]:has(.sahay-landing-feature) [data-testid="stMarkdownContainer"] {
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    height: 100%;
}
.sahay-landing-feature {
    height: 100%;
    display: flex;
    flex-direction: column;
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
.sahay-landing-feature:hover {
    transform: translateY(-3px);
    border-color: rgba(139,133,193,0.4);
    box-shadow: 0 14px 30px rgba(47,93,138,0.16), 0 4px 12px rgba(63,175,160,0.10);
}
.sahay-landing-feature-icon { font-size: 22px; margin-bottom: 8px; }
.sahay-landing-feature-title { font-weight: 700; margin-bottom: 4px; }

/* ---------- Closing section ---------- */
.sahay-landing-closing {
    text-align: center;
    padding: 1.4rem 1rem;
}
.sahay-landing-closing h3 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.25rem;
    margin-bottom: 4px;
}

/* ---------- Footer ---------- */
.sahay-landing-footer {
    text-align: center;
    color: #9CA3AF;
    font-size: 12px;
    padding: 18px 0 6px 0;
    border-top: 1px solid var(--sahay-border);
    margin-top: 8px;
}

/* ---------- Responsive ----------
   Streamlit already stacks st.columns() vertically and collapses the
   sidebar below ~640px — these rules only tighten spacing/type on top of
   that, same pattern as components/theme.py's own responsive block. */
@media (max-width: 768px) {
    .sahay-landing-topnav {
        padding: 0.7rem 1.1rem;
        flex-wrap: wrap;
        row-gap: 8px;
    }
    .sahay-admin-link {
        padding: 6px 12px;
        font-size: 12px;
    }
    div[class*="st-key-sahay_landing_hero"] { padding: 1.6rem 1.3rem; }
    .sahay-landing-hero h1 { font-size: 1.6rem; }
    .sahay-landing-hero-sub { font-size: 14.5px; }
}
</style>
"""


def render_landing_page() -> None:
    st.markdown(_LANDING_CSS, unsafe_allow_html=True)
    st.markdown(_google_icon_css(), unsafe_allow_html=True)
    _topnav()
    _auth_error_banner()
    _hero()
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    _auth_forms()
    st.markdown("<div style='height:36px'></div>", unsafe_allow_html=True)
    _feature_grid()
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    _safety_notice()
    _closing_cta()
    _footer()


def _topnav() -> None:
    """Fixed top bar carrying the Sahay wordmark + BETA badge that used to
    sit inline at the top of the hero column (Phase 2 and earlier) —
    repositioned here, not removed, so the hero itself can lead with the
    headline.

    PHASE (Admin Panel entry point, approved): a plain `<a href="?admin=1">`
    anchor was added on the right side of this same bar. This is a real
    browser link, not a Streamlit widget — clicking it navigates to the
    exact same `?admin=1` URL `streamlit_app.py`'s existing admin gate
    already checks (`st.query_params.get("admin")`, unchanged). No new
    session-state, no new widget key, no change to admin_auth.py or the
    gate itself — this is only a visible entry point to what was already
    reachable, just previously unlinked from the landing page.
    """
    st.markdown(
        f"""
        <div class="sahay-landing-topnav">
            <div style="display:flex;align-items:center;gap:10px;">
                {sahay_icon_html(26)}
                <span class="sahay-display" style="font-weight:700;font-size:16px;">Sahay AI</span>
                <span style="background:{COLORS['soft_teal']}22;color:{COLORS['soft_teal']};
                    padding:2px 10px;border-radius:999px;font-size:11px;font-weight:600;">BETA</span>
            </div>
            <a href="?admin=1" class="sahay-admin-link" target="_self">
                🛡️ Admin Panel
            </a>
        </div>
        <div class="sahay-landing-topnav-spacer"></div>
        """,
        unsafe_allow_html=True,
    )


def _auth_error_banner() -> None:
    error = st.session_state.pop("sahay_auth_error", None)
    if error:
        st.error(error)


def _hero() -> None:
    """PHASE (hero layout fix + wellness visual, approved):

    Previously this function opened `<div class="sahay-landing-hero">`
    via one `st.markdown()` call, rendered the actual content via
    `st.columns()`, then closed `</div>` via a SECOND, separate
    `st.markdown()` call. Streamlit renders each `st.markdown()` as its
    own isolated DOM block — it does not nest widgets rendered by other
    calls inside a tag opened in an earlier one. The browser therefore
    auto-closed the first call's unclosed div immediately, producing an
    empty div carrying the hero's gradient/shadow/radius styling with no
    content inside it (the reported "blank rectangle"), while the real
    headline/subtitle/accent-card rendered as an unstyled sibling block
    beneath it.

    Fixed by using `st.container(key="sahay_landing_hero")` — a real
    Streamlit layout primitive whose auto-generated `st-key-...` class
    (targeted in _LANDING_CSS) is a genuine DOM ancestor of everything
    rendered inside the `with` block below, so the hero background now
    actually wraps its content. This also gave a safe place to add the
    approved decorative floating glyphs and the "Check In -> Reflect ->
    Relax -> Get Support" strip — both pure CSS/HTML, no new
    functionality, no backend calls, no session-state.
    """
    with st.container(key="sahay_landing_hero"):
        # Decorative only — pointer-events:none in CSS, so these never
        # intercept clicks on the real content rendered below them.
        st.markdown(
            """
            <span class="sahay-hero-glyph sahay-hero-glyph-1">💬</span>
            <span class="sahay-hero-glyph sahay-hero-glyph-2">🌱</span>
            <span class="sahay-hero-glyph sahay-hero-glyph-3">❤️</span>
            <span class="sahay-hero-glyph sahay-hero-glyph-4">🧘</span>
            <span class="sahay-hero-glyph sahay-hero-glyph-5">☀️</span>
            """,
            unsafe_allow_html=True,
        )

        left, right = st.columns([3, 2])
        with left:
            st.markdown(
                "<h1>Your AI Companion<br>for Student Wellbeing.</h1>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<p class='sahay-landing-hero-sub' style='color:{COLORS['muted_dark']};'>"
                "Reflect on how you're feeling, manage everyday student stress, explore "
                "wellness activities, and find appropriate support when you need it.</p>",
                unsafe_allow_html=True,
            )
            st.caption("Secure sign-in via Supabase Auth · No judgment · Your data stays yours")

        with right:
            st.markdown(
                f"""
                <div class="sahay-accent-card" style="height:100%;display:flex;
                     flex-direction:column;justify-content:center;text-align:center;padding:40px 24px;">
                    {sahay_icon_html(52)}
                    <p style="font-size:19px;font-weight:700;margin:14px 0 4px 0;">Meet Sahay</p>
                    <p class="sahay-card-caption">A calm, supportive AI wellness companion —
                    not a therapist, doctor, or diagnosis tool.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            """
            <div class="sahay-hero-journey">
                <span class="sahay-hero-journey-step">🙂 Check In</span>
                <span class="sahay-hero-journey-arrow">→</span>
                <span class="sahay-hero-journey-step">💬 Reflect</span>
                <span class="sahay-hero-journey-arrow">→</span>
                <span class="sahay-hero-journey-step">🧘 Relax</span>
                <span class="sahay-hero-journey-arrow">→</span>
                <span class="sahay-hero-journey-step">🤝 Get Support</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _auth_forms() -> None:
    with st.container(border=True):
        _google_button()
        st.markdown("<div style='text-align:center;color:#9CA3AF;font-size:12px;margin:10px 0;'>or</div>", unsafe_allow_html=True)

        tab_login, tab_signup, tab_reset = st.tabs(["Log In", "Sign Up", "Forgot Password"])

        with tab_login:
            _login_form()

        with tab_signup:
            _signup_form()

        with tab_reset:
            _reset_form()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("Continue in Demo Mode →", key="landing_demo_btn"):
            st.session_state["sahay_view"] = "app"
            st.session_state["sahay_demo_mode"] = True
            st.rerun()
        st.caption("No account needed — a preview with sample data only. Nothing you do in Demo Mode is saved.")


def _google_button() -> None:
    """PHASE (Google icon, approved): the 🔵 emoji prefix was removed from
    all three label strings below; a proper multicolor Google "G" is now
    supplied by CSS (`.sahay-google-icon` / `--sahay-google-icon`, see
    _LANDING_CSS and _google_icon_css()) via a `::before` background-image
    on the button/link itself. `st.link_button` did not previously take a
    `key=` — one was added (`landing_google_link_btn`) purely so CSS can
    scope the icon to this specific link and not
    pages/government_services.py's own unrelated `st.link_button` calls.
    A link_button's key has no session-state/behavioral effect (it only
    navigates), so this does not change OAuth logic, add app state, or
    alter any existing widget's behavior. Every backend call below
    (`auth.get_google_sign_in_url()`, the `except auth.AuthError` handling)
    is byte-identical to before."""
    if not (SUPABASE_USER_CONFIG.is_configured and GOOGLE_OAUTH_CONFIG.is_configured):
        if st.button("Continue with Google", key="landing_google_btn", use_container_width=True):
            st.info("Google Sign-In will be available once Supabase and Google OAuth are configured. See PHASE2_IMPLEMENTATION_REPORT.md for setup steps.")
        return

    from backend import auth
    try:
        url = auth.get_google_sign_in_url()
        st.link_button("Continue with Google", url, key="landing_google_link_btn", use_container_width=True)
        st.caption("Google Sign-In is configured but has not been live-tested in this environment (no network access). Please verify it end-to-end yourself.")
    except auth.AuthError as exc:
        st.button("Continue with Google", key="landing_google_btn_err", use_container_width=True, disabled=True)
        st.caption(str(exc))


def _login_form() -> None:
    with st.form("login_form", border=False):
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Log In", use_container_width=True, type="primary")
    if submitted:
        if not email or not password:
            st.warning("Please enter both your email and password.")
            return
        from backend import auth
        try:
            auth.sign_in_with_password(email, password)
            st.session_state["sahay_view"] = "app"
            st.session_state["sahay_demo_mode"] = False
            st.rerun()
        except auth.AuthError as exc:
            st.error(str(exc))
        except Exception as exc:  # noqa: BLE001 - Supabase not configured, etc.
            st.error("Sign-in isn't available right now. Please try again later.")
            st.caption(f"Technical detail (dev preview only): {exc}")


def _signup_form() -> None:
    with st.form("signup_form", border=False):
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password", help="At least 8 characters.")
        confirm = st.text_input("Confirm password", type="password", key="signup_confirm")
        submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")
    if submitted:
        if not email or not password:
            st.warning("Please enter an email and password.")
            return
        if password != confirm:
            st.warning("Passwords don't match.")
            return
        from backend import auth
        try:
            auth.sign_up(email, password)
            st.success("Account created. Check your email if verification is required, then log in.")
        except auth.AuthError as exc:
            st.error(str(exc))
        except Exception as exc:  # noqa: BLE001
            st.error("Sign-up isn't available right now. Please try again later.")
            st.caption(f"Technical detail (dev preview only): {exc}")


def _reset_form() -> None:
    with st.form("reset_form", border=False):
        email = st.text_input("Email", key="reset_email")
        submitted = st.form_submit_button("Send Reset Link", use_container_width=True)
    if submitted:
        if not email:
            st.warning("Please enter your email.")
            return
        from backend import auth
        try:
            auth.reset_password_for_email(email)
            st.success("If an account exists for that email, a reset link is on its way.")
        except Exception as exc:  # noqa: BLE001
            st.error("Couldn't send a reset link right now. Please try again later.")
            st.caption(f"Technical detail (dev preview only): {exc}")


def _feature_grid() -> None:
    st.markdown("<h2 class='sahay-landing-section-title'>What Sahay can help with</h2>", unsafe_allow_html=True)
    cols = st.columns(4)
    for i, (icon, title, desc) in enumerate(FEATURES):
        with cols[i]:
            st.markdown(
                f"""
                <div class="sahay-card sahay-landing-feature">
                    <div class="sahay-landing-feature-icon">{icon}</div>
                    <div class="sahay-landing-feature-title">{title}</div>
                    <div class="sahay-card-caption">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _safety_notice() -> None:
    st.markdown(
        f"""
        <div class="sahay-card" style="border-left:4px solid {COLORS['soft_teal']};">
            <div style="font-weight:700;margin-bottom:4px;">🔒 Safety &amp; privacy first</div>
            <div class="sahay-card-caption">
                Sahay is AI-powered student wellness support and guidance — it does not
                diagnose, prescribe, or replace a doctor, therapist, or counselor. If
                you're ever in crisis, the Human Help section connects you to real
                support. Your account data is private to you, protected by
                database-level access rules — not just app-level checks.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _closing_cta() -> None:
    """Text-only closing section (no new widgets, no new session-state
    writes) pointing back to the sign-in area above — the "Final CTA"
    slot from the Phase 3 spec, without duplicating the Log In/Sign
    Up/Demo Mode controls a second time on the same page."""
    st.markdown(
        """
        <div class="sahay-landing-closing">
            <h3>Ready to explore Sahay AI?</h3>
            <p class="sahay-card-caption">Sign in, create an account, or continue in Demo Mode above — no pressure, no commitment.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _footer() -> None:
    st.markdown(
        "<div class='sahay-landing-footer'>"
        "Sahay AI · Student wellness companion · Edunet Foundation × IBM SkillsBuild internship project"
        "</div>",
        unsafe_allow_html=True,
    )

"""
components/page_components/
----------------------------
PHASE 6B: reusable, presentation-only building blocks shared across the
14 Sahay user-dashboard pages, introduced per the Phase 6A audit's
duplication analysis (see PHASE6A_INDIVIDUAL_PAGE_AUDIT.md §8/§14).

Every component in this package:
  - renders UI only — no Supabase/OpenRouter/backend imports anywhere
    in this package (verified in PHASE6B_REPORT.md §7);
  - accepts content/data as plain arguments, never a backend/DB object;
  - never performs navigation (`sahay_page` writes), never touches any
    of the CRITICAL session-state keys catalogued in Phase 5/6A
    (`sahay_active_conversation_id`, `sahay_last_mood`,
    `sahay_chat_history`, `sahay_dark_mode`, etc.) — the one place a
    component keeps any session state of its own
    (`confirm_action.render_confirm_action`'s open/closed flag) uses a
    component-private key namespace (`_confirm_action_open__<key>`)
    that cannot collide with any existing page key;
    - reads `st.session_state.get("sahay_dark_mode", False)` the same
    way components/chatbot_launcher.py already does, to pick
    light/dark colors from components/theme.py's existing COLORS dict —
    no second color system, no new dark-mode key.

No individual page imports from this package yet — Phase 6B only
builds the components; page migration is a later, separately-approved
phase (Phase 6C+).
"""

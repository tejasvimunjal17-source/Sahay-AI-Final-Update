"""
components/topbar.py
---------------------
Top utility bar + page header for the authenticated Sahay AI dashboard.
No auth or notification data is real yet (layout only — same scope note
as Phase 1).

PHASE 4 (LearnMate-style dashboard shell): restyled into an elevated
"page header" card — date/utility row + large page title — sitting at
the top of the main content area. Deliberately NOT `position: fixed`
like LearnMate's own `.lm-topnav`: that bar is `z-index: 999` while
LearnMate's sidebar drawer is `z-index: 999998`, so LearnMate's fixed
topnav is actually covered by its own drawer along the left ~21rem
whenever the drawer is open — a quirk of that implementation, not
something worth reproducing here. Sitting in normal document flow means
this bar naturally shifts with the rest of the main content when
components/sidebar.py's drawer opens/closes, with no extra CSS needed
and no overlap risk. Signature is UNCHANGED
(`render_topbar(page_title: str) -> None`) — streamlit_app.py's call
site needed no changes.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from components.theme import COLORS


def render_topbar(page_title: str) -> None:
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;justify-content:space-between;
             padding:14px 20px;border-radius:var(--sahay-radius, 18px);
             border:1px solid var(--sahay-border, rgba(20,24,33,0.08));
             box-shadow:var(--sahay-shadow, 0 4px 20px rgba(20,24,33,0.06));
             margin-bottom:20px;">
            <div>
                <div style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:22px;">
                    {page_title}
                </div>
                <div style="color:#6B7280;font-size:12.5px;margin-top:2px;">
                    {datetime.now().strftime('%A, %d %B %Y')}
                </div>
            </div>
            <div style="color:#6B7280;font-size:16px;">🔔 &nbsp; 👤</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

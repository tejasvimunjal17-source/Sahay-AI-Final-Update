"""
admin/views.py
-----------------
PHASE 7 IMPLEMENTATION.

The six admin content areas (Dashboard/Usage/Mood, User Management,
Feedback, Safety Events, System Health/Configuration), all reading
through backend.admin_data — which itself only ever returns aggregates,
counts, or (for feedback only, a deliberate and documented exception —
see admin_data.get_feedback_summary's docstring) explicitly-submitted
feedback text. NO view in this file ever renders a student's
conversation or message content.
"""

from __future__ import annotations

import streamlit as st

from backend.admin_auth import AdminUser


def _fmt_count(value) -> str:
    """None means the count couldn't be read — show a dash, never a fake 0."""
    return "—" if value is None else f"{value:,}"


def render_dashboard(admin: AdminUser) -> None:
    from backend import admin_data
    import pandas as pd

    st.markdown("### Dashboard")
    st.caption("Aggregate usage and wellness signal — never individual conversations.")

    window_days = st.selectbox(
        "Time window", [7, 30, 90], index=1, key="admin_dash_window",
        format_func=lambda d: f"Last {d} days",
    )

    try:
        usage = admin_data.get_usage_summary(admin, days=window_days)
        mood = admin_data.get_mood_distribution(admin, days=window_days)
        languages = admin_data.get_language_usage(admin)
        activities = admin_data.get_activity_usage(admin, days=window_days)
    except Exception as exc:  # noqa: BLE001
        st.error("Couldn't load dashboard data right now.")
        st.caption(f"Technical detail (dev preview only): {exc}")
        return

    # Extra signals are additive: if they fail, the original dashboard still renders.
    try:
        overview = admin_data.get_dashboard_overview(admin, days=window_days)
    except Exception as exc:  # noqa: BLE001
        overview = None
        st.warning("Some additional dashboard signals couldn't be loaded.")
        st.caption(f"Technical detail (dev preview only): {exc}")

    # --- Original headline metrics (unchanged) ---
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total users", usage["total_users"])
    with c2:
        st.metric(f"Active users (last {usage['window_days']}d)", usage["active_users"])
    with c3:
        st.metric("Total conversations", usage["total_conversations"])

    if overview:
        totals, in_window = overview["totals"], overview["in_window"]
        st.markdown("##### Overview")
        r1 = st.columns(3)
        r1[0].metric(f"New users (last {window_days}d)", overview["new_users_in_window"])
        r1[1].metric("New users (last 7d)", overview["new_users_7d"])
        r1[2].metric("Onboarding completed", f"{overview['onboarded_users']} / {overview['total_users']}")
        r2 = st.columns(3)
        r2[0].metric(f"Messages (last {window_days}d)", _fmt_count(in_window["messages"]),
                     help="Count only — message text is never read by the admin panel.")
        r2[1].metric(f"Mood events (last {window_days}d)", _fmt_count(in_window["mood_events"]))
        r2[2].metric(f"Wellness activities (last {window_days}d)", _fmt_count(in_window["wellness_activities_completed"]))
        r3 = st.columns(3)
        r3[0].metric("Feedback entries (all time)", _fmt_count(totals["feedback"]))
        r3[1].metric(f"Safety events (last {window_days}d)", _fmt_count(in_window["safety_events"]))
        r3[2].metric("Admin-role accounts", overview["admin_role_users"])

        st.markdown("##### New registrations — last 14 days")
        signups = overview["signups_last_14_days"]
        if any(signups.values()):
            st.line_chart(pd.DataFrame({"New registrations": list(signups.values())}, index=list(signups.keys())))
        else:
            st.caption("No new registrations in the last 14 days.")

    if usage["conversations_by_day"]:
        st.markdown("##### Conversations by day")
        st.bar_chart(usage["conversations_by_day"])

    if mood:
        st.markdown("##### Approximate mood distribution (all users)")
        st.bar_chart(mood)

    if languages:
        st.markdown("##### Language usage")
        st.bar_chart(languages)

    if activities:
        st.markdown("##### Wellness activity usage")
        st.bar_chart(activities)

    if overview and overview["recent_registrations"]:
        st.markdown("##### Recent registrations")
        for r in overview["recent_registrations"]:
            st.write(f"**{r['display_name']}** · joined {r['created_at']}")


_USERS_PAGE_SIZE = 10
_USER_SORTS = {
    "Newest first": ("created_at", True),
    "Oldest first": ("created_at", False),
    "Name (A–Z)": ("display_name", False),
    "Name (Z–A)": ("display_name", True),
}


def render_users(admin: AdminUser) -> None:
    from backend import admin_data
    st.markdown("### User Management")
    st.caption("Profile summaries only — display name, role, language, and account age. No conversation content.")

    try:
        users = admin_data.list_users(admin, limit=1000)
    except Exception as exc:  # noqa: BLE001
        st.error("Couldn't load users right now.")
        st.caption(f"Technical detail (dev preview only): {exc}")
        return

    if not users:
        st.info("No users yet.")
        return

    # --- Summary cards (all derived from the loaded profiles) ---
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Users", len(users))
    s2.metric("Students", sum(1 for u in users if u.get("role") != "admin"))
    s3.metric("Admin role", sum(1 for u in users if u.get("role") == "admin"))
    s4.metric("Onboarded", sum(1 for u in users if u.get("onboarding_complete")))

    # --- Search / filter / sort ---
    search = st.text_input("Search by display name", key="admin_users_search", placeholder="Type part of a name…")
    f1, f2, f3 = st.columns(3)
    role_filter = f1.selectbox("Role", ["All", "student", "admin"], key="admin_users_role")
    languages = sorted({u.get("preferred_language") or "en" for u in users})
    lang_filter = f2.selectbox("Language", ["All", *languages], key="admin_users_lang")
    onboard_filter = f3.selectbox("Onboarding", ["All", "Completed", "Not completed"], key="admin_users_onboard")
    sort_label = st.selectbox("Sort by", list(_USER_SORTS), key="admin_users_sort")

    filtered = users
    if search.strip():
        needle = search.strip().lower()
        filtered = [u for u in filtered if needle in (u.get("display_name") or "").lower()]
    if role_filter != "All":
        filtered = [u for u in filtered if (u.get("role") or "student") == role_filter]
    if lang_filter != "All":
        filtered = [u for u in filtered if (u.get("preferred_language") or "en") == lang_filter]
    if onboard_filter != "All":
        want = onboard_filter == "Completed"
        filtered = [u for u in filtered if bool(u.get("onboarding_complete")) == want]
    sort_key, reverse = _USER_SORTS[sort_label]
    filtered = sorted(filtered, key=lambda u: (u.get(sort_key) or "").lower(), reverse=reverse)

    st.caption(f"{len(filtered)} of {len(users)} user(s) match.")
    if not filtered:
        st.info("No users match the current search/filters.")
        return

    # --- Pagination ---
    total_pages = max(1, -(-len(filtered) // _USERS_PAGE_SIZE))
    page = 1
    if total_pages > 1:
        page = int(st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1, key="admin_users_page"))
        st.caption(f"Page {page} of {total_pages}")
    page_users = filtered[(page - 1) * _USERS_PAGE_SIZE: page * _USERS_PAGE_SIZE]

    # --- Existing per-user row + role toggle (behaviour unchanged) ---
    for u in page_users:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{u.get('display_name') or '(no display name)'}**")
                onboarded = "Yes" if u.get("onboarding_complete") else "No"
                st.caption(
                    f"Role: {u.get('role', 'student')} · Language: {u.get('preferred_language', 'en')} · "
                    f"Onboarded: {onboarded} · Joined: {u.get('created_at', '')[:10]}"
                )
            with col2:
                is_admin_role = u.get("role") == "admin"
                label = "Revoke admin" if is_admin_role else "Promote to admin"
                if st.button(label, key=f"admin_role_toggle_{u['id']}"):
                    try:
                        admin_data.set_user_role(admin, u["id"], "student" if is_admin_role else "admin")
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.error("Couldn't update this user's role.")
                        st.caption(f"Technical detail (dev preview only): {exc}")

    # --- Inspect a user: engagement counts only ---
    st.markdown("---")
    st.markdown("##### Inspect a user")
    st.caption("Engagement counts and last activity only — no message text, mood values, or safety data.")
    options = {
        f"{u.get('display_name') or '(no display name)'} — {u['id'][:8]}": u for u in filtered
    }
    choice = st.selectbox("Select a user", list(options), key="admin_users_inspect")
    selected = options[choice]
    try:
        summary = admin_data.get_user_activity_summary(admin, selected["id"])
    except Exception as exc:  # noqa: BLE001
        st.error("Couldn't load this user's activity right now.")
        st.caption(f"Technical detail (dev preview only): {exc}")
        return

    st.write(
        f"**{selected.get('display_name') or '(no display name)'}** · role: {selected.get('role', 'student')} · "
        f"language: {selected.get('preferred_language', 'en')} · registered: {selected.get('created_at', '')[:10]}"
    )
    last = summary["last_activity"]
    st.caption(f"Last activity: {last[:16].replace('T', ' ')} UTC" if last else "Last activity: no recorded activity yet")
    a1, a2, a3 = st.columns(3)
    a1.metric("Conversations", _fmt_count(summary["conversations"]))
    a2.metric("Messages", _fmt_count(summary["messages"]))
    a3.metric("Mood check-ins", _fmt_count(summary["mood_checkins"]))
    b1, b2 = st.columns(2)
    b1.metric("Wellness activities", _fmt_count(summary["wellness_activities"]))
    b2.metric("Feedback submitted", _fmt_count(summary["feedback_submitted"]))


def render_feedback(admin: AdminUser) -> None:
    from backend import admin_data
    st.markdown("### Feedback Management")
    st.caption("Feedback is explicitly submitted by students for the app's maintainers to read.")

    try:
        summary = admin_data.get_feedback_summary(admin)
    except Exception as exc:  # noqa: BLE001
        st.error("Couldn't load feedback right now.")
        st.caption(f"Technical detail (dev preview only): {exc}")
        return

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Total feedback entries", summary["total_count"])
    with c2:
        st.metric("Average rating", summary["average_rating"] if summary["average_rating"] is not None else "—")

    if summary["rating_distribution"]:
        st.markdown("##### Rating distribution")
        st.bar_chart(summary["rating_distribution"])

    if not summary["recent"]:
        st.info("No feedback submitted yet.")
        return

    st.markdown("##### Recent feedback")
    for f in summary["recent"]:
        with st.container(border=True):
            st.markdown(f"Rating: {f.get('rating', '—')}/5 · {f.get('created_at', '')[:16].replace('T', ' ')}")
            if f.get("message"):
                st.write(f["message"])


def render_safety(admin: AdminUser) -> None:
    from backend import admin_data
    st.markdown("### Safety Event Monitoring")
    st.caption(
        "Counts of deterministic safety-rule outcomes only — category and action, "
        "never the message content that triggered them."
    )

    try:
        summary = admin_data.get_safety_event_summary(admin)
    except Exception as exc:  # noqa: BLE001
        st.error("Couldn't load safety events right now.")
        st.caption(f"Technical detail (dev preview only): {exc}")
        return

    st.metric(f"Safety events (last {summary['window_days']}d)", summary["total_in_window"])

    if summary["by_category"]:
        st.markdown("##### By category")
        st.bar_chart(summary["by_category"])

    if summary["by_action"]:
        st.markdown("##### By action")
        st.bar_chart(summary["by_action"])

    if not summary["by_category"]:
        st.info("No safety events recorded in this window.")


def render_system(admin: AdminUser) -> None:
    from backend import admin_data
    st.markdown("### System Health & Configuration")
    st.caption("Configuration status only — never secret values.")

    status = admin_data.get_configuration_status()
    labels = {
        "supabase_user_configured": "Supabase (student access)",
        "supabase_admin_configured": "Supabase (admin/service-role access)",
        "openrouter_configured": "OpenRouter (AI engine)",
        "google_oauth_configured": "Google OAuth",
    }
    for key, label in labels.items():
        configured = status.get(key, False)
        icon = "✅" if configured else "⚠️"
        st.write(f"{icon} {label}: {'Configured' if configured else 'Not configured'}")

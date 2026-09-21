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


def render_dashboard(admin: AdminUser) -> None:
    from backend import admin_data
    st.markdown("### Dashboard")
    st.caption("Aggregate usage and wellness signal — never individual conversations.")

    try:
        usage = admin_data.get_usage_summary(admin)
        mood = admin_data.get_mood_distribution(admin)
        languages = admin_data.get_language_usage(admin)
        activities = admin_data.get_activity_usage(admin)
    except Exception as exc:  # noqa: BLE001
        st.error("Couldn't load dashboard data right now.")
        st.caption(f"Technical detail (dev preview only): {exc}")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total users", usage["total_users"])
    with c2:
        st.metric(f"Active users (last {usage['window_days']}d)", usage["active_users"])
    with c3:
        st.metric("Total conversations", usage["total_conversations"])

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


def render_users(admin: AdminUser) -> None:
    from backend import admin_data
    st.markdown("### User Management")
    st.caption("Profile summaries only — display name, role, language, and account age. No conversation content.")

    try:
        users = admin_data.list_users(admin)
    except Exception as exc:  # noqa: BLE001
        st.error("Couldn't load users right now.")
        st.caption(f"Technical detail (dev preview only): {exc}")
        return

    if not users:
        st.info("No users yet.")
        return

    for u in users:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{u.get('display_name') or '(no display name)'}**")
                st.caption(f"Role: {u.get('role', 'student')} · Language: {u.get('preferred_language', 'en')} · Joined: {u.get('created_at', '')[:10]}")
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

-- =============================================================================
-- 013_safety_events.sql
-- Sahay AI — Phase 7: safety event monitoring
-- =============================================================================
-- Logs ONLY non-"allow" outcomes from chatbot/safety.py's deterministic
-- screening (crisis / block), for the admin "Safety Event Monitoring"
-- feature. Deliberately minimal: user_id, timestamp, category, and the
-- action taken — NEVER the message content, the AI's reply, or any other
-- conversation text. This is a security/monitoring artifact, not a
-- clinical or content record.
--
-- Written via the service-role client (mirrors backend/audit_log.py's
-- existing pattern for audit_logs) — students never read this table
-- directly; RLS is enabled with zero policies, same default-deny
-- treatment as audit_logs and admin_users.
-- =============================================================================

create table if not exists public.safety_events (
    id          bigint generated always as identity primary key,
    user_id     uuid references auth.users (id) on delete set null,
    category    text not null,   -- e.g. 'self_harm_or_violence', 'dangerous_medical_instruction_request',
                                  -- 'medical_diagnosis_request', 'medication_request',
                                  -- 'dependency_or_replace_professional_help', 'prompt_injection'
    action      text not null check (action in ('crisis', 'block')),
    created_at  timestamptz not null default now()
);

comment on table public.safety_events is
    'Minimal safety-event log for admin monitoring: WHO (user_id), WHEN, '
    'WHAT CATEGORY of deterministic safety rule fired, and whether it was '
    'a crisis or block outcome. Never stores message content, the AI '
    'reply, or any other conversation text — see chatbot/response_generator.py '
    'for where this is (optionally, best-effort) written.';

alter table public.safety_events enable row level security;
-- Deliberately no policies for anon/authenticated — service-role-only,
-- identical treatment to audit_logs (001/002) and admin_users (011).

create index if not exists idx_safety_events_created_at on public.safety_events (created_at desc);
create index if not exists idx_safety_events_category on public.safety_events (category);

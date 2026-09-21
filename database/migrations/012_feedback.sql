-- =============================================================================
-- 012_feedback.sql
-- Sahay AI — Phase 7: minimal feedback collection
-- =============================================================================
-- Built now because Feedback Management is an explicit Phase 7 admin
-- feature (master spec §25) with nothing to manage otherwise. Minimal by
-- design: a rating + optional short message, owned by the submitting
-- user, RLS-scoped exactly like every other Phase 4/5 table. Admins read
-- it in aggregate (see backend/admin_data.py) via the service-role
-- client — same pattern as every other admin-analytics read.
-- =============================================================================

create table if not exists public.feedback (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references auth.users (id) on delete cascade,
    rating      smallint check (rating between 1 and 5),
    message     text,
    created_at  timestamptz not null default now()
);

comment on table public.feedback is
    'Simple student feedback: an optional 1-5 rating and an optional '
    'short message. Owned by the submitting user; admins read this in '
    'aggregate via the service-role client, never treating individual '
    'messages as anything beyond optional free-text a student chose to '
    'share.';

alter table public.feedback enable row level security;

drop policy if exists "feedback_select_own" on public.feedback;
create policy "feedback_select_own" on public.feedback
    for select to authenticated using (auth.uid() = user_id);

drop policy if exists "feedback_insert_own" on public.feedback;
create policy "feedback_insert_own" on public.feedback
    for insert to authenticated with check (auth.uid() = user_id);

-- No UPDATE/DELETE policy: feedback, once submitted, is immutable from
-- the student's side — matches how `messages` (005) already treats
-- submitted content as append-only.

create index if not exists idx_feedback_created_at on public.feedback (created_at desc);

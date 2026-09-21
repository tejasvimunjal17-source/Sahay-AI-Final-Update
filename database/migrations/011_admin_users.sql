-- =============================================================================
-- 011_admin_users.sql
-- Sahay AI — Phase 7: admin accounts
-- =============================================================================
-- Admins are NOT Supabase Auth users — this is a deliberately separate,
-- independent auth system (bcrypt password hash), matching the pattern
-- audited from LearnMate AI in PHASE0_AUDIT.md §B. admin_users has NO
-- foreign key to auth.users and NO RLS policy granting anon/authenticated
-- access at all — same default-deny pattern as audit_logs (002/008).
-- Every read/write goes through the service-role client
-- (backend/admin_auth.py), never a student's anon-key session.
--
-- No public sign-up path exists or will ever exist for this table — the
-- first admin account is created via a documented manual procedure (see
-- README.md "Creating the first admin account"), never hardcoded and
-- never auto-provisioned by application code.
-- =============================================================================

create table if not exists public.admin_users (
    id             uuid primary key default gen_random_uuid(),
    email          text not null unique,
    password_hash  text not null,
    display_name   text,
    is_active      boolean not null default true,
    created_at     timestamptz not null default now(),
    last_login_at  timestamptz
);

comment on table public.admin_users is
    'Independent admin accounts — bcrypt password hash, no relation to '
    'auth.users. Service-role access only (see backend/admin_auth.py); '
    'no RLS policy exists for anon/authenticated roles by design.';

alter table public.admin_users enable row level security;
-- Deliberately no policies created — see comment above and
-- 002_rls_policies.sql's identical treatment of audit_logs.

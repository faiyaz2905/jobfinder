create extension if not exists pgcrypto;

create table if not exists public.companies (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  career_url text not null,
  category text not null default '',
  ats_type text not null default 'generic',
  ats_identifier text not null default '',
  notes text not null default '',
  linkedin_slug text not null default '',
  facebook_url text not null default '',
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists companies_name_normalized_key
  on public.companies (lower(name));

create table if not exists public.postings (
  id text primary key,
  company_id uuid references public.companies(id) on delete set null,
  company text not null,
  role text not null,
  apply_action text not null,
  source text not null,
  source_url text not null,
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  status text not null default 'new'
    check (status in ('new', 'saved', 'applied', 'interviewing', 'rejected', 'offer', 'archived')),
  applied_at timestamptz,
  notified_at timestamptz,
  notes text not null default ''
);

create index if not exists postings_first_seen_idx
  on public.postings (first_seen_at desc);
create index if not exists postings_company_idx
  on public.postings (company);

create table if not exists public.contacts (
  id text primary key,
  company_id uuid references public.companies(id) on delete set null,
  company text not null,
  email text not null,
  source_page text not null,
  contact_type text not null default 'generic',
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now()
);

create unique index if not exists contacts_company_email_key
  on public.contacts (lower(company), lower(email));

create table if not exists public.scan_runs (
  id uuid primary key default gen_random_uuid(),
  trigger text not null check (trigger in ('scheduled', 'manual')),
  status text not null default 'running'
    check (status in ('running', 'succeeded', 'partial', 'failed', 'skipped')),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  companies_checked integer not null default 0,
  postings_seen integer not null default 0,
  new_postings integer not null default 0,
  notification_status text not null default 'not_needed'
    check (notification_status in ('not_needed', 'pending', 'sent', 'failed')),
  error_summary jsonb not null default '[]'::jsonb
);

create index if not exists scan_runs_started_idx
  on public.scan_runs (started_at desc);

create table if not exists public.scan_locks (
  name text primary key,
  owner text not null,
  expires_at timestamptz not null
);

create or replace function public.acquire_scan_lock(
  lock_name text,
  lock_owner text,
  ttl_seconds integer default 290
)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
begin
  delete from public.scan_locks
  where name = lock_name and expires_at <= now();

  insert into public.scan_locks(name, owner, expires_at)
  values (
    lock_name,
    lock_owner,
    now() + make_interval(secs => greatest(30, least(ttl_seconds, 600)))
  )
  on conflict (name) do nothing;

  return exists (
    select 1 from public.scan_locks
    where name = lock_name and owner = lock_owner and expires_at > now()
  );
end;
$$;

create or replace function public.release_scan_lock(lock_name text, lock_owner text)
returns boolean
language sql
security definer
set search_path = public
as $$
  with deleted as (
    delete from public.scan_locks
    where name = lock_name and owner = lock_owner
    returning 1
  )
  select exists(select 1 from deleted);
$$;

alter table public.companies enable row level security;
alter table public.postings enable row level security;
alter table public.contacts enable row level security;
alter table public.scan_runs enable row level security;
alter table public.scan_locks enable row level security;

revoke all on function public.acquire_scan_lock(text, text, integer) from public, anon, authenticated;
revoke all on function public.release_scan_lock(text, text) from public, anon, authenticated;
grant execute on function public.acquire_scan_lock(text, text, integer) to service_role;
grant execute on function public.release_scan_lock(text, text) to service_role;

-- The browser never queries these tables directly. Vercel Functions use the
-- service-role key after validating the user's Supabase session and allowlist.

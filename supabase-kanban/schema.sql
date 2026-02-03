-- Run this in Supabase SQL editor
create table if not exists public.tasks (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  status text not null default 'backlog' check (status in ('backlog','in_progress','done')),
  created_at timestamptz not null default now()
);

alter table public.tasks enable row level security;

-- Allow anon to read/write (no-auth MVP)
create policy "anon read" on public.tasks
  for select using (true);

create policy "anon insert" on public.tasks
  for insert with check (true);

create policy "anon update" on public.tasks
  for update using (true);

-- Optional: allow delete if needed
-- create policy "anon delete" on public.tasks
--   for delete using (true);

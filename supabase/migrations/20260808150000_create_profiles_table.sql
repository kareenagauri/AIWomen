-- Migration: create_profiles_table
-- Creates the profiles table (1:1 with auth.users), RLS policies,
-- an auto-create-on-signup trigger, and an auto-update-updated_at trigger.

-- 1. Table
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  career_field text,
  location_city text,
  location_region text,
  location_country text,
  bio text,
  onboarding_completed boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 2. Enable Row Level Security
alter table public.profiles enable row level security;

-- 3. RLS policies: a user may read and update only their own row.
-- No INSERT policy (rows are created by the trigger below, not by clients).
-- No DELETE policy (deletion happens via auth.users cascade, not directly).
create policy "Users can view own profile"
  on public.profiles
  for select
  using (auth.uid() = id);

create policy "Users can update own profile"
  on public.profiles
  for update
  using (auth.uid() = id)
  with check (auth.uid() = id);

-- 4. Function + trigger: automatically create a profile row
-- whenever a new user is created in auth.users.
create function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id)
  values (new.id);
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row
  execute function public.handle_new_user();

-- 5. Function + trigger: automatically keep updated_at current
-- on every update to a profiles row.
create function public.handle_profiles_updated_at()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger on_profiles_updated
  before update on public.profiles
  for each row
  execute function public.handle_profiles_updated_at();

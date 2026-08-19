-- Migration: create_saved_content
-- Feature 1 (Content Details + Save): lets a user bookmark a content item.
-- Additive only — no existing table/migration touched.

create table public.saved_content (
  user_id uuid not null references public.profiles(id) on delete cascade,
  content_id uuid not null references public.content_items(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (user_id, content_id)
);

alter table public.saved_content enable row level security;

-- No secondary index: the composite PK's leading column (user_id) already
-- serves the only query pattern this feature needs ("get my saved items").
-- Nothing queries "who saved content X", unlike content_goals/content_interests.

create policy "Users can view own saved content"
  on public.saved_content
  for select
  using (auth.uid() = user_id);

create policy "Users can save content for themselves"
  on public.saved_content
  for insert
  with check (auth.uid() = user_id);

create policy "Users can remove own saved content"
  on public.saved_content
  for delete
  using (auth.uid() = user_id);

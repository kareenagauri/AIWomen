-- Migration: create_content_enrichments
-- AI-generated structured enrichment (summary, skills, topics, optional
-- experience level) for content_items, kept in its own table so ingestion
-- never needs AI-awareness and re-ingestion never clobbers AI output (or
-- vice versa). One row per content item — a re-run overwrites via upsert
-- on content_id ("latest wins"); model/prompt_version/source_content_hash
-- record what produced the current row and let a later run detect when
-- it's outdated, without keeping multi-row history. No raw AI response is
-- stored — only the validated, structured fields actually needed.

create table public.content_enrichments (
  content_id uuid primary key references public.content_items(id) on delete cascade,
  summary text not null,
  skills jsonb not null default '[]'::jsonb check (jsonb_typeof(skills) = 'array'),
  topics jsonb not null default '[]'::jsonb check (jsonb_typeof(topics) = 'array'),
  experience_level text check (experience_level in ('entry', 'mid', 'senior')),
  model text not null,
  prompt_version text not null,
  source_content_hash text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.content_enrichments enable row level security;

-- No SELECT/INSERT/UPDATE/DELETE policy for anon or authenticated roles:
-- written and read only via the service-role client used by offline
-- scripts (app/ingestion/run_enrich_content.py), same confinement already
-- enforced for ingestion. Nothing in this phase exposes enrichment data
-- through the API, so no public read policy is added yet — a later phase
-- that surfaces summary/skills to users adds its own explicit, narrower
-- read policy then.

create function public.handle_content_enrichments_updated_at()
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

create trigger on_content_enrichments_updated
  before update on public.content_enrichments
  for each row
  execute function public.handle_content_enrichments_updated_at();

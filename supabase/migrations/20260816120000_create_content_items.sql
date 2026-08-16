-- Migration: create_content_items
-- Unified content model (career + wellness) for Stage 6A, plus tagging
-- junctions to goals/interests, RLS (public read only), indexes, and
-- clearly-fictional representative seed data (source='seed').

-- 1. content_items
create table public.content_items (
  id uuid primary key default gen_random_uuid(),
  category text not null check (category in ('career', 'wellness')),
  content_type text not null check (
    content_type in ('job', 'program', 'scholarship', 'event', 'article', 'video', 'local_resource')
  ),
  title text not null,
  description text,
  url text,
  organization text,
  location_city text,
  location_region text,
  location_country text,
  is_remote boolean not null default false,
  event_date timestamptz,
  deadline timestamptz,
  published_at timestamptz,
  source text not null default 'seed',
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.content_items enable row level security;

create policy "Content is publicly readable"
  on public.content_items
  for select
  using (true);

-- Recommendation query filters by category + active first, then narrows
-- by location — these are the two indexes that pattern actually needs.
create index content_items_category_active_idx
  on public.content_items (category, is_active);

create index content_items_location_city_idx
  on public.content_items (location_city);

create function public.handle_content_items_updated_at()
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

create trigger on_content_items_updated
  before update on public.content_items
  for each row
  execute function public.handle_content_items_updated_at();

-- 2. content_goals (junction: content_items <-> goals)
create table public.content_goals (
  content_id uuid not null references public.content_items(id) on delete cascade,
  goal_id uuid not null references public.goals(id) on delete cascade,
  primary key (content_id, goal_id)
);

alter table public.content_goals enable row level security;

create policy "Content goal tags are publicly readable"
  on public.content_goals
  for select
  using (true);

-- The composite PK's leading column (content_id) serves "tags of this
-- content item." Recommendation scoring queries the opposite direction —
-- "which content is tagged with goal X" — which needs its own index,
-- unlike user_goals where that direction was never actually queried.
create index content_goals_goal_id_idx
  on public.content_goals (goal_id);

-- 3. content_interests (junction: content_items <-> interests)
create table public.content_interests (
  content_id uuid not null references public.content_items(id) on delete cascade,
  interest_id uuid not null references public.interests(id) on delete cascade,
  primary key (content_id, interest_id)
);

alter table public.content_interests enable row level security;

create policy "Content interest tags are publicly readable"
  on public.content_interests
  for select
  using (true);

create index content_interests_interest_id_idx
  on public.content_interests (interest_id);

-- 4. Seed data — CLEARLY FICTIONAL representative records for development
-- and testing only. Titles/organizations are bracketed "[Sample] ..." and
-- URLs point at example.com. None of this represents a real organization,
-- opportunity, or listing. source='seed' identifies these as non-real.
insert into public.content_items
  (category, content_type, title, description, url, organization,
   location_city, location_region, location_country, is_remote,
   event_date, deadline, published_at, source)
values
  ('career', 'job', '[Sample] Software Engineer, Women-in-Tech Returnship',
   'Illustrative sample listing for a returnship-style software engineering role aimed at women re-entering tech after a career break.',
   'https://example.com/sample-job-returnship', '[Sample Company] Returnship Program',
   'Bengaluru', 'Karnataka', 'India', false,
   null, now() + interval '21 days', now() - interval '5 days', 'seed'),

  ('career', 'scholarship', '[Sample] Women in Leadership Scholarship',
   'Illustrative sample scholarship supporting women pursuing leadership or management education.',
   'https://example.com/sample-scholarship-leadership', '[Sample Foundation]',
   null, null, 'India', true,
   null, now() + interval '45 days', now() - interval '10 days', 'seed'),

  ('career', 'program', '[Sample] Career Transition Mentorship Program',
   'Illustrative sample mentorship program for women transitioning into a new industry.',
   'https://example.com/sample-program-mentorship', '[Sample Mentorship Network]',
   null, null, null, true,
   null, null, now() - interval '40 days', 'seed'),

  ('career', 'event', '[Sample] Women in Tech Networking Meetup',
   'Illustrative sample in-person networking event for women working in technology.',
   'https://example.com/sample-event-networking', '[Sample Tech Community]',
   'Bengaluru', 'Karnataka', 'India', false,
   now() + interval '14 days', null, now() - interval '3 days', 'seed'),

  ('career', 'article', '[Sample] Negotiating Salary with Confidence',
   'Illustrative sample article covering salary negotiation strategies.',
   'https://example.com/sample-article-negotiation', '[Sample Publication]',
   null, null, null, true,
   null, null, now() - interval '60 days', 'seed'),

  ('career', 'program', '[Sample] Remote Work Skills Bootcamp',
   'Illustrative sample bootcamp on tools and practices for effective remote work.',
   'https://example.com/sample-program-remote', '[Sample Learning Collective]',
   null, null, null, true,
   null, now() + interval '10 days', now() - interval '2 days', 'seed'),

  ('wellness', 'article', '[Sample] Five-Minute Stress Reset Techniques',
   'Illustrative sample article on brief stress-management techniques for busy schedules.',
   'https://example.com/sample-article-stress', '[Sample Wellness Publication]',
   null, null, null, true,
   null, null, now() - interval '8 days', 'seed'),

  ('wellness', 'video', '[Sample] Guided Mindfulness Meditation (10 min)',
   'Illustrative sample short guided meditation video for daily mindfulness practice.',
   'https://example.com/sample-video-meditation', '[Sample Wellness Channel]',
   null, null, null, true,
   null, null, now() - interval '1 days', 'seed'),

  ('wellness', 'local_resource', '[Sample] Community Fitness Studio',
   'Illustrative sample local fitness studio offering women-focused classes.',
   'https://example.com/sample-local-fitness', '[Sample Fitness Studio]',
   'Bengaluru', 'Karnataka', 'India', false,
   null, null, now() - interval '90 days', 'seed'),

  ('wellness', 'event', '[Sample] Mental Health Awareness Workshop',
   'Illustrative sample workshop on mental health awareness and self-care practices.',
   'https://example.com/sample-event-mentalhealth', '[Sample Wellness Org]',
   'Bengaluru', 'Karnataka', 'India', false,
   now() + interval '7 days', null, now() - interval '4 days', 'seed'),

  ('wellness', 'program', '[Sample] Working Parents Support Circle',
   'Illustrative sample peer support program for working parents.',
   'https://example.com/sample-program-parents', '[Sample Parenting Network]',
   null, null, null, true,
   null, null, now() - interval '20 days', 'seed'),

  ('wellness', 'article', '[Sample] Budgeting Basics for Career Changers',
   'Illustrative sample article on financial planning during a career transition.',
   'https://example.com/sample-article-budgeting', '[Sample Finance Publication]',
   null, null, null, true,
   null, null, now() - interval '70 days', 'seed');

-- 5. Seed tagging: content_goals
with content_goal_map (content_title, goal_slug) as (
  values
    ('[Sample] Software Engineer, Women-in-Tech Returnship', 'return-to-work'),
    ('[Sample] Software Engineer, Women-in-Tech Returnship', 'career-transition'),
    ('[Sample] Women in Leadership Scholarship', 'leadership-skills'),
    ('[Sample] Career Transition Mentorship Program', 'career-transition'),
    ('[Sample] Career Transition Mentorship Program', 'networking-growth'),
    ('[Sample] Women in Tech Networking Meetup', 'networking-growth'),
    ('[Sample] Negotiating Salary with Confidence', 'salary-negotiation'),
    ('[Sample] Remote Work Skills Bootcamp', 'skill-development'),
    ('[Sample] Five-Minute Stress Reset Techniques', 'work-life-balance'),
    ('[Sample] Mental Health Awareness Workshop', 'work-life-balance'),
    ('[Sample] Working Parents Support Circle', 'work-life-balance'),
    ('[Sample] Budgeting Basics for Career Changers', 'career-transition')
)
insert into public.content_goals (content_id, goal_id)
select ci.id, g.id
from content_goal_map m
join public.content_items ci on ci.title = m.content_title
join public.goals g on g.slug = m.goal_slug;

-- 6. Seed tagging: content_interests
with content_interest_map (content_title, interest_slug) as (
  values
    ('[Sample] Software Engineer, Women-in-Tech Returnship', 'women-in-tech'),
    ('[Sample] Career Transition Mentorship Program', 'women-in-tech'),
    ('[Sample] Women in Tech Networking Meetup', 'women-in-tech'),
    ('[Sample] Remote Work Skills Bootcamp', 'remote-work'),
    ('[Sample] Five-Minute Stress Reset Techniques', 'stress-management'),
    ('[Sample] Guided Mindfulness Meditation (10 min)', 'mindfulness-meditation'),
    ('[Sample] Community Fitness Studio', 'fitness-nutrition'),
    ('[Sample] Mental Health Awareness Workshop', 'mental-health'),
    ('[Sample] Working Parents Support Circle', 'parenting-support'),
    ('[Sample] Budgeting Basics for Career Changers', 'financial-literacy')
)
insert into public.content_interests (content_id, interest_id)
select ci.id, i.id
from content_interest_map m
join public.content_items ci on ci.title = m.content_title
join public.interests i on i.slug = m.interest_slug;

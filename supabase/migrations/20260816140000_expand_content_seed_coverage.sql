-- Migration: expand_content_seed_coverage
-- Additive seed-data fix for Stage 6A: adds 3 new content items so every
-- goal and interest has at least one tagged item, without touching any
-- existing content_items/content_goals/content_interests rows. All new
-- items are clearly-fictional samples (title/organization bracketed,
-- example.com URLs, source='seed'), same convention as the prior migration.

-- content_items has no natural unique key, so idempotency here is done via
-- an explicit "insert only if a row with this title doesn't already exist"
-- guard, keyed on title (unique within this seed set by construction,
-- though not database-enforced).
with new_items (
  category, content_type, title, description, url, organization,
  location_city, location_region, location_country, is_remote,
  event_date, deadline, published_at, source
) as (
  values
    ('career', 'program', '[Sample] Return-to-Work Career Restart Program',
     'Illustrative sample structured program helping women returning to the workforce refresh technical skills and rebuild confidence, delivered remotely.',
     'https://example.com/sample-program-return-to-work', '[Sample Career Restart Network]',
     null, null, null, true,
     null, now() + interval '30 days', now() - interval '6 days', 'seed'),

    ('career', 'program', '[Sample] Women Founders Entrepreneurship Accelerator',
     'Illustrative sample accelerator program supporting early-stage women-led ventures with mentorship, funding guidance, and peer networking.',
     'https://example.com/sample-program-accelerator', '[Sample Founders Accelerator]',
     null, null, null, true,
     null, now() + interval '35 days', now() - interval '15 days', 'seed'),

    ('career', 'event', '[Sample] Public Speaking & Creative Confidence Workshop',
     'Illustrative sample workshop building public speaking and presentation confidence through creative and performance-based exercises.',
     'https://example.com/sample-event-publicspeaking', '[Sample Confidence Collective]',
     null, null, null, true,
     now() + interval '12 days', null, now() - interval '2 days', 'seed')
)
insert into public.content_items
  (category, content_type, title, description, url, organization,
   location_city, location_region, location_country, is_remote,
   event_date, deadline, published_at, source)
select
  category, content_type, title, description, url, organization,
  location_city, location_region, location_country, is_remote,
  event_date, deadline, published_at, source
from new_items
where not exists (
  select 1 from public.content_items ci where ci.title = new_items.title
);

-- Tagging: resolve goal ids via slug (never hardcoded UUIDs). ON CONFLICT
-- DO NOTHING makes this safe against re-application, using the junction
-- table's real composite primary key.
with content_goal_map (content_title, goal_slug) as (
  values
    ('[Sample] Return-to-Work Career Restart Program', 'return-to-work'),
    ('[Sample] Return-to-Work Career Restart Program', 'skill-development'),
    ('[Sample] Women Founders Entrepreneurship Accelerator', 'entrepreneurship'),
    ('[Sample] Women Founders Entrepreneurship Accelerator', 'networking-growth'),
    ('[Sample] Public Speaking & Creative Confidence Workshop', 'leadership-skills'),
    ('[Sample] Public Speaking & Creative Confidence Workshop', 'salary-negotiation')
)
insert into public.content_goals (content_id, goal_id)
select ci.id, g.id
from content_goal_map m
join public.content_items ci on ci.title = m.content_title
join public.goals g on g.slug = m.goal_slug
on conflict (content_id, goal_id) do nothing;

-- Tagging: resolve interest ids via slug, same idempotency approach.
with content_interest_map (content_title, interest_slug) as (
  values
    ('[Sample] Return-to-Work Career Restart Program', 'women-in-tech'),
    ('[Sample] Return-to-Work Career Restart Program', 'remote-work'),
    ('[Sample] Women Founders Entrepreneurship Accelerator', 'women-in-tech'),
    ('[Sample] Women Founders Entrepreneurship Accelerator', 'financial-literacy'),
    ('[Sample] Public Speaking & Creative Confidence Workshop', 'public-speaking'),
    ('[Sample] Public Speaking & Creative Confidence Workshop', 'creative-arts')
)
insert into public.content_interests (content_id, interest_id)
select ci.id, i.id
from content_interest_map m
join public.content_items ci on ci.title = m.content_title
join public.interests i on i.slug = m.interest_slug
on conflict (content_id, interest_id) do nothing;

-- Migration: create_goals_interests
-- Creates goals, interests lookup tables and user_goals, user_interests
-- junction tables, plus seed data for the onboarding UI.

-- 1. goals (curated lookup table)
create table public.goals (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  label text not null,
  description text,
  created_at timestamptz not null default now()
);

alter table public.goals enable row level security;

create policy "Goals are publicly readable"
  on public.goals
  for select
  using (true);

-- 2. interests (curated lookup table)
create table public.interests (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  label text not null,
  description text,
  created_at timestamptz not null default now()
);

alter table public.interests enable row level security;

create policy "Interests are publicly readable"
  on public.interests
  for select
  using (true);

-- 3. user_goals (junction: profiles <-> goals)
create table public.user_goals (
  user_id uuid not null references public.profiles(id) on delete cascade,
  goal_id uuid not null references public.goals(id) on delete cascade,
  primary key (user_id, goal_id)
);

alter table public.user_goals enable row level security;

create policy "Users can view own goals"
  on public.user_goals
  for select
  using (auth.uid() = user_id);

create policy "Users can add own goals"
  on public.user_goals
  for insert
  with check (auth.uid() = user_id);

create policy "Users can remove own goals"
  on public.user_goals
  for delete
  using (auth.uid() = user_id);

-- 4. user_interests (junction: profiles <-> interests)
create table public.user_interests (
  user_id uuid not null references public.profiles(id) on delete cascade,
  interest_id uuid not null references public.interests(id) on delete cascade,
  primary key (user_id, interest_id)
);

alter table public.user_interests enable row level security;

create policy "Users can view own interests"
  on public.user_interests
  for select
  using (auth.uid() = user_id);

create policy "Users can add own interests"
  on public.user_interests
  for insert
  with check (auth.uid() = user_id);

create policy "Users can remove own interests"
  on public.user_interests
  for delete
  using (auth.uid() = user_id);

-- 5. Seed data: goals
insert into public.goals (slug, label, description) values
  ('career-transition', 'Transition to a New Career', 'For users looking to pivot industries or roles'),
  ('leadership-skills', 'Build Leadership Skills', 'Growing into management or senior leadership roles'),
  ('return-to-work', 'Return to Work After a Break', 'Re-entering the workforce after time away'),
  ('skill-development', 'Learn New Professional Skills', 'Upskilling or reskilling for career growth'),
  ('entrepreneurship', 'Start or Grow a Business', 'Launching or scaling an independent venture'),
  ('salary-negotiation', 'Improve Salary Negotiation Skills', 'Building confidence in compensation conversations'),
  ('networking-growth', 'Grow My Professional Network', 'Building mentorship and peer connections'),
  ('work-life-balance', 'Achieve Better Work-Life Balance', 'Managing career alongside personal life demands')
on conflict (slug) do nothing;

-- 6. Seed data: interests
insert into public.interests (slug, label, description) values
  ('stress-management', 'Stress Management', 'Resources for managing everyday stress'),
  ('mental-health', 'Mental Health Support', 'Resources related to emotional and mental wellbeing'),
  ('fitness-nutrition', 'Fitness & Nutrition', 'Physical fitness, movement, and nutrition resources'),
  ('mindfulness-meditation', 'Mindfulness & Meditation', 'Meditation, breathing, and mindfulness practices'),
  ('remote-work', 'Remote Work', 'Remote and flexible work opportunities'),
  ('women-in-tech', 'Women in Tech', 'Technology-focused career resources and communities'),
  ('financial-literacy', 'Financial Literacy', 'Budgeting, saving, and financial planning resources'),
  ('parenting-support', 'Parenting Support', 'Resources for working parents and caregivers'),
  ('public-speaking', 'Public Speaking & Confidence', 'Communication and confidence-building resources'),
  ('creative-arts', 'Creative Arts', 'Creative and artistic wellness outlets')
on conflict (slug) do nothing;

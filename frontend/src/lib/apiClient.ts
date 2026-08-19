import { supabase } from './supabaseClient'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

if (!API_BASE_URL) {
  throw new Error('Missing VITE_API_BASE_URL. Check frontend/.env.')
}

/**
 * Fetch wrapper for protected FastAPI endpoints. Pulls the current session
 * from Supabase at call time (never a cached/stale token) and attaches it
 * as a Bearer token. Reused by every API function rather than duplicating
 * this per page.
 */
export async function authorizedFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (!session) {
    throw new Error('No active session — user is not authenticated.')
  }

  const headers = new Headers(init.headers)
  headers.set('Authorization', `Bearer ${session.access_token}`)

  return fetch(`${API_BASE_URL}${path}`, { ...init, headers })
}

async function throwForError(response: Response, label: string): Promise<never> {
  let detail = ''
  try {
    const body = (await response.json()) as { detail?: string }
    detail = body.detail ? ` — ${body.detail}` : ''
  } catch {
    // Response body wasn't JSON (or was empty) — fall back to the plain
    // status-based message below.
  }
  throw new Error(`${label} failed with status ${response.status}${detail}`)
}

async function parseJsonOrThrow<T>(response: Response, label: string): Promise<T> {
  if (!response.ok) {
    return throwForError(response, label)
  }
  return response.json() as Promise<T>
}

/** For endpoints that return no body (e.g. 204 No Content) — just asserts
 * success or throws with the same error-detail handling as parseJsonOrThrow. */
async function assertOk(response: Response, label: string): Promise<void> {
  if (!response.ok) {
    await throwForError(response, label)
  }
}

export interface MeResponse {
  user_id: string
}

export async function fetchMe(): Promise<MeResponse> {
  const response = await authorizedFetch('/api/me')
  return parseJsonOrThrow<MeResponse>(response, 'GET /api/me')
}

export interface Profile {
  id: string
  display_name: string | null
  career_field: string | null
  location_city: string | null
  location_region: string | null
  location_country: string | null
  bio: string | null
  onboarding_completed: boolean
  created_at: string
  updated_at: string
}

export interface ProfileUpdateInput {
  display_name?: string | null
  career_field?: string | null
  location_city?: string | null
  location_region?: string | null
  location_country?: string | null
  bio?: string | null
}

export async function fetchProfile(): Promise<Profile> {
  const response = await authorizedFetch('/api/profile/me')
  return parseJsonOrThrow<Profile>(response, 'GET /api/profile/me')
}

export async function updateProfile(input: ProfileUpdateInput): Promise<Profile> {
  const response = await authorizedFetch('/api/profile/me', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  return parseJsonOrThrow<Profile>(response, 'PUT /api/profile/me')
}

export async function completeOnboarding(): Promise<Profile> {
  const response = await authorizedFetch('/api/profile/me/complete-onboarding', {
    method: 'POST',
  })
  return parseJsonOrThrow<Profile>(response, 'POST /api/profile/me/complete-onboarding')
}

export interface TagOption {
  id: string
  slug: string
  label: string
  description: string | null
}

export interface OnboardingOptions {
  goals: TagOption[]
  interests: TagOption[]
}

export async function fetchOnboardingOptions(): Promise<OnboardingOptions> {
  const response = await authorizedFetch('/api/onboarding/options')
  return parseJsonOrThrow<OnboardingOptions>(response, 'GET /api/onboarding/options')
}

export async function fetchMyGoals(): Promise<TagOption[]> {
  const response = await authorizedFetch('/api/profile/me/goals')
  return parseJsonOrThrow<TagOption[]>(response, 'GET /api/profile/me/goals')
}

export async function replaceMyGoals(goalIds: string[]): Promise<TagOption[]> {
  const response = await authorizedFetch('/api/profile/me/goals', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ goal_ids: goalIds }),
  })
  return parseJsonOrThrow<TagOption[]>(response, 'PUT /api/profile/me/goals')
}

export async function fetchMyInterests(): Promise<TagOption[]> {
  const response = await authorizedFetch('/api/profile/me/interests')
  return parseJsonOrThrow<TagOption[]>(response, 'GET /api/profile/me/interests')
}

export async function replaceMyInterests(interestIds: string[]): Promise<TagOption[]> {
  const response = await authorizedFetch('/api/profile/me/interests', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ interest_ids: interestIds }),
  })
  return parseJsonOrThrow<TagOption[]>(response, 'PUT /api/profile/me/interests')
}

/** Fields common to every shape content is displayed in — the feed, the
 * details page, and the saved list — so each of those only adds what's
 * actually different about it. */
export interface DisplayableContent {
  id: string
  category: 'career' | 'wellness'
  content_type: string
  title: string
  description: string | null
  url: string | null
  organization: string | null
  location_city: string | null
  location_region: string | null
  location_country: string | null
  is_remote: boolean
  event_date: string | null
  deadline: string | null
  published_at: string | null
}

export interface RecommendationItem extends DisplayableContent {
  score: number
  matched_goal_ids: string[]
  matched_interest_ids: string[]
}

export async function fetchRecommendations(
  category?: 'career' | 'wellness',
): Promise<RecommendationItem[]> {
  const query = category ? `?category=${category}` : ''
  const response = await authorizedFetch(`/api/recommendations${query}`)
  return parseJsonOrThrow<RecommendationItem[]>(response, 'GET /api/recommendations')
}

export interface ContentDetail extends DisplayableContent {
  matched_goal_ids: string[]
  matched_interest_ids: string[]
  is_saved: boolean
}

export async function fetchContentDetail(contentId: string): Promise<ContentDetail> {
  const response = await authorizedFetch(`/api/content/${contentId}`)
  return parseJsonOrThrow<ContentDetail>(response, 'GET /api/content/{id}')
}

export interface SavedContentItem extends DisplayableContent {
  saved_at: string
}

export async function fetchSavedContent(): Promise<SavedContentItem[]> {
  const response = await authorizedFetch('/api/saved')
  return parseJsonOrThrow<SavedContentItem[]>(response, 'GET /api/saved')
}

export async function saveContent(contentId: string): Promise<void> {
  const response = await authorizedFetch(`/api/saved/${contentId}`, { method: 'POST' })
  await assertOk(response, 'POST /api/saved/{id}')
}

export async function removeSavedContent(contentId: string): Promise<void> {
  const response = await authorizedFetch(`/api/saved/${contentId}`, { method: 'DELETE' })
  await assertOk(response, 'DELETE /api/saved/{id}')
}

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

async function parseJsonOrThrow<T>(response: Response, label: string): Promise<T> {
  if (!response.ok) {
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
  return response.json() as Promise<T>
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

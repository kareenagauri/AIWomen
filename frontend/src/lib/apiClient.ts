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

export interface MeResponse {
  user_id: string
}

export async function fetchMe(): Promise<MeResponse> {
  const response = await authorizedFetch('/api/me')

  if (!response.ok) {
    throw new Error(`GET /api/me failed with status ${response.status}`)
  }

  return response.json() as Promise<MeResponse>
}

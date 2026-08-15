import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    'Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY. Check frontend/.env.',
  )
}

// Session persistence/refresh is handled entirely by supabase-js's default
// behavior — we never read or write the access token ourselves.
export const supabase = createClient(supabaseUrl, supabaseAnonKey)

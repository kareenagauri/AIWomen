import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import {
  fetchOnboardingOptions,
  fetchRecommendations,
  fetchSavedContent,
  removeSavedContent,
  saveContent,
  type RecommendationItem,
} from '../lib/apiClient'
import { formatContentType } from '../lib/formatters'
import { CategoryFilter } from './CategoryFilter'
import { PillFilter } from './PillFilter'
import { RecommendationCard } from './RecommendationCard'
import { SearchBar } from './SearchBar'

type Category = 'career' | 'wellness' | undefined
type LocationPreference = 'remote' | 'local' | undefined

const CONTENT_TYPES = [
  'job',
  'program',
  'scholarship',
  'event',
  'article',
  'video',
  'local_resource',
] as const

const CONTENT_TYPE_OPTIONS: { label: string; value: string | undefined }[] = [
  { label: 'All', value: undefined },
  ...CONTENT_TYPES.map((type) => ({ label: formatContentType(type), value: type as string })),
]

const LOCATION_OPTIONS: { label: string; value: LocationPreference }[] = [
  { label: 'All', value: undefined },
  { label: 'Remote', value: 'remote' },
  { label: 'Local', value: 'local' },
]

export function HomePage() {
  const { user, signOut } = useAuth()

  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [goalLabels, setGoalLabels] = useState<Map<string, string>>(new Map())
  const [interestLabels, setInterestLabels] = useState<Map<string, string>>(new Map())
  const [items, setItems] = useState<RecommendationItem[]>([])
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set())

  const [category, setCategory] = useState<Category>(undefined)
  const [contentType, setContentType] = useState<string | undefined>(undefined)
  const [location, setLocation] = useState<LocationPreference>(undefined)
  const [submittedSearch, setSubmittedSearch] = useState('')

  const hasActiveFilters = Boolean(category || contentType || location || submittedSearch)

  const isFirstFilterEffectRun = useRef(true)

  // Initial load: onboarding options (for match labels), the first
  // recommendations fetch, and the user's saved-content ids — together,
  // nothing renders until all three resolve. No filters are active yet at
  // this point, so this is equivalent to fetchRecommendations({ category }).
  useEffect(() => {
    let cancelled = false

    Promise.all([
      fetchOnboardingOptions(),
      fetchRecommendations({ category }),
      fetchSavedContent(),
    ])
      .then(([options, recommendations, saved]) => {
        if (cancelled) return
        setGoalLabels(new Map(options.goals.map((g) => [g.id, g.label])))
        setInterestLabels(new Map(options.interests.map((i) => [i.id, i.label])))
        setItems(recommendations)
        setSavedIds(new Set(saved.map((s) => s.id)))
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
    // Runs once on mount only; filter/search changes are handled by the
    // effect below, which explicitly skips this same initial run.
  }, [])

  // Any filter or a submitted search changing after the initial load:
  // re-fetch recommendations only — onboarding options and saved ids are
  // unaffected, and the list itself is never re-sorted or re-filtered on
  // the client, only replaced with whatever the server returns.
  useEffect(() => {
    if (isFirstFilterEffectRun.current) {
      isFirstFilterEffectRun.current = false
      return
    }

    let cancelled = false
    setUpdating(true)
    setError(null)

    fetchRecommendations({
      category,
      content_type: contentType,
      location,
      search: submittedSearch,
    })
      .then((recommendations) => {
        if (!cancelled) setItems(recommendations)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err))
      })
      .finally(() => {
        if (!cancelled) setUpdating(false)
      })

    return () => {
      cancelled = true
    }
  }, [category, contentType, location, submittedSearch])

  async function handleToggleSave(contentId: string) {
    const alreadySaved = savedIds.has(contentId)
    if (alreadySaved) {
      await removeSavedContent(contentId)
      setSavedIds((prev) => {
        const next = new Set(prev)
        next.delete(contentId)
        return next
      })
    } else {
      await saveContent(contentId)
      setSavedIds((prev) => new Set(prev).add(contentId))
    }
  }

  if (loading) {
    return <p style={{ textAlign: 'center', marginTop: '4rem' }}>Loading your recommendations...</p>
  }

  return (
    <div style={{ maxWidth: 640, margin: '3rem auto', padding: '0 1rem' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          marginBottom: '1.5rem',
        }}
      >
        <div>
          <h1 style={{ margin: 0 }}>For you</h1>
          <p style={{ margin: '0.25rem 0 0', color: '#666' }}>{user?.email}</p>
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <Link to="/profile">Profile</Link>
          <Link to="/saved">Saved</Link>
          <button type="button" onClick={() => signOut()}>
            Log out
          </button>
        </div>
      </div>

      <SearchBar initialValue={submittedSearch} onSubmit={setSubmittedSearch} />

      <CategoryFilter value={category} onChange={setCategory} />
      <PillFilter options={CONTENT_TYPE_OPTIONS} value={contentType} onChange={setContentType} />
      <PillFilter options={LOCATION_OPTIONS} value={location} onChange={setLocation} />

      {error && <p style={{ color: 'crimson' }}>{error}</p>}

      {!error && updating && <p style={{ color: '#666' }}>Updating recommendations...</p>}

      {!error && !updating && items.length === 0 && (
        <p style={{ color: '#666' }}>
          {hasActiveFilters
            ? 'No recommendations match your current filters.'
            : 'No recommendations match your profile yet. Try adjusting your goals or interests, or check back soon as new content is added.'}
        </p>
      )}

      {!error &&
        items.map((item) => (
          <RecommendationCard
            key={item.id}
            item={item}
            matchedGoalIds={item.matched_goal_ids}
            matchedInterestIds={item.matched_interest_ids}
            goalLabels={goalLabels}
            interestLabels={interestLabels}
            isSaved={savedIds.has(item.id)}
            onToggleSave={() => handleToggleSave(item.id)}
          />
        ))}
    </div>
  )
}

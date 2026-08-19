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
import { CategoryFilter } from './CategoryFilter'
import { RecommendationCard } from './RecommendationCard'

type Category = 'career' | 'wellness' | undefined

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

  const isFirstCategoryEffectRun = useRef(true)

  // Initial load: onboarding options (for match labels), the first
  // recommendations fetch, and the user's saved-content ids — together,
  // nothing renders until all three resolve.
  useEffect(() => {
    let cancelled = false

    Promise.all([fetchOnboardingOptions(), fetchRecommendations(category), fetchSavedContent()])
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
    // Runs once on mount only; category changes are handled by the effect
    // below, which explicitly skips this same initial run.
  }, [])

  // Category changes after the initial load: re-fetch recommendations only
  // — onboarding options and saved ids are unaffected by category, and the
  // list itself is never re-sorted or re-filtered on the client, only
  // replaced with whatever the server returns for the new category.
  useEffect(() => {
    if (isFirstCategoryEffectRun.current) {
      isFirstCategoryEffectRun.current = false
      return
    }

    let cancelled = false
    setUpdating(true)
    setError(null)

    fetchRecommendations(category)
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
  }, [category])

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

      <CategoryFilter value={category} onChange={setCategory} />

      {error && <p style={{ color: 'crimson' }}>{error}</p>}

      {!error && updating && <p style={{ color: '#666' }}>Updating...</p>}

      {!error && !updating && items.length === 0 && (
        <p style={{ color: '#666' }}>
          No recommendations match your profile yet. Try adjusting your goals or interests, or
          check back soon as new content is added.
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

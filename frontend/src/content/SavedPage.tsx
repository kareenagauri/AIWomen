import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchSavedContent, removeSavedContent, type SavedContentItem } from '../lib/apiClient'
import { RecommendationCard } from '../home/RecommendationCard'

export function SavedPage() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [items, setItems] = useState<SavedContentItem[]>([])

  useEffect(() => {
    let cancelled = false

    fetchSavedContent()
      .then((saved) => {
        if (!cancelled) setItems(saved)
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
  }, [])

  async function handleRemove(contentId: string) {
    await removeSavedContent(contentId)
    setItems((prev) => prev.filter((item) => item.id !== contentId))
  }

  if (loading) {
    return <p style={{ textAlign: 'center', marginTop: '4rem' }}>Loading your saved items...</p>
  }

  return (
    <div style={{ maxWidth: 640, margin: '3rem auto', padding: '0 1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '1.5rem' }}>
        <h1 style={{ margin: 0 }}>Saved</h1>
        <Link to="/">← Back to your feed</Link>
      </div>

      {error && <p style={{ color: 'crimson' }}>{error}</p>}

      {!error && items.length === 0 && (
        <p style={{ color: '#666' }}>
          You haven&apos;t saved anything yet. Explore your feed and save items you want to come
          back to.
        </p>
      )}

      {!error &&
        items.map((item) => (
          <RecommendationCard
            key={item.id}
            item={item}
            isSaved
            onToggleSave={() => handleRemove(item.id)}
          />
        ))}
    </div>
  )
}

import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { DisplayableContent } from '../lib/apiClient'
import { formatContentType, formatDateLine, formatLocation, formatRecency } from '../lib/formatters'

interface RecommendationCardProps {
  item: DisplayableContent
  matchedGoalIds?: string[]
  matchedInterestIds?: string[]
  goalLabels?: Map<string, string>
  interestLabels?: Map<string, string>
  isSaved: boolean
  onToggleSave: () => Promise<void>
}

/** Purely presentational — takes already-fetched data as props, never
 * fetches anything itself and never touches Supabase or apiClient. Reused
 * by both the home feed and the saved-content list. */
export function RecommendationCard({
  item,
  matchedGoalIds = [],
  matchedInterestIds = [],
  goalLabels = new Map(),
  interestLabels = new Map(),
  isSaved,
  onToggleSave,
}: RecommendationCardProps) {
  const [savePending, setSavePending] = useState(false)

  const location = formatLocation(item.is_remote, item.location_city, item.location_country)
  const dateLine = formatDateLine(item.deadline, item.event_date)
  const recency = formatRecency(item.published_at)

  // Unresolved ids are silently dropped rather than shown as raw UUIDs or
  // surfaced as an error.
  const matchedGoalLabels = matchedGoalIds
    .map((id) => goalLabels.get(id))
    .filter((label): label is string => Boolean(label))
  const matchedInterestLabels = matchedInterestIds
    .map((id) => interestLabels.get(id))
    .filter((label): label is string => Boolean(label))

  const hasMatches = matchedGoalLabels.length > 0 || matchedInterestLabels.length > 0

  async function handleToggleSave() {
    setSavePending(true)
    try {
      await onToggleSave()
    } finally {
      setSavePending(false)
    }
  }

  return (
    <article
      style={{
        border: '1px solid #e2e2e2',
        borderRadius: 8,
        padding: '1.25rem',
        marginBottom: '1rem',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem' }}>
        <span style={{ fontSize: '0.75rem', color: '#888', textTransform: 'uppercase' }}>
          {formatContentType(item.content_type)}
        </span>
        {recency && <span style={{ fontSize: '0.75rem', color: '#888' }}>{recency}</span>}
      </div>

      <h3 style={{ margin: '0.25rem 0' }}>{item.title}</h3>

      {item.organization && <p style={{ margin: '0.25rem 0', color: '#555' }}>{item.organization}</p>}

      {item.description && <p style={{ margin: '0.5rem 0' }}>{item.description}</p>}

      {(location || dateLine) && (
        <div style={{ display: 'flex', gap: '1rem', fontSize: '0.875rem', color: '#555' }}>
          {location && <span>{location}</span>}
          {dateLine && <span>{dateLine}</span>}
        </div>
      )}

      {hasMatches && (
        <p style={{ marginTop: '0.75rem', fontSize: '0.875rem', color: '#2d6a4f' }}>
          Matches{' '}
          {matchedGoalLabels.length > 0 && <>your goal: {matchedGoalLabels.join(', ')}</>}
          {matchedGoalLabels.length > 0 && matchedInterestLabels.length > 0 && ' · '}
          {matchedInterestLabels.length > 0 && <>your interest: {matchedInterestLabels.join(', ')}</>}
        </p>
      )}

      <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', marginTop: '0.75rem' }}>
        <Link to={`/content/${item.id}`}>Explore →</Link>
        <button type="button" onClick={() => void handleToggleSave()} disabled={savePending}>
          {isSaved ? 'Saved' : 'Save'}
        </button>
      </div>
    </article>
  )
}

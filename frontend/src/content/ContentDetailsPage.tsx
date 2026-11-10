import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  fetchContentDetail,
  fetchOnboardingOptions,
  removeSavedContent,
  saveContent,
  type ContentDetail,
} from '../lib/apiClient'
import {
  formatContentType,
  formatCtaLabel,
  formatDateLine,
  formatLocation,
  formatRecency,
} from '../lib/formatters'

export function ContentDetailsPage() {
  const { id } = useParams<{ id: string }>()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [content, setContent] = useState<ContentDetail | null>(null)
  const [goalLabels, setGoalLabels] = useState<Map<string, string>>(new Map())
  const [interestLabels, setInterestLabels] = useState<Map<string, string>>(new Map())
  const [isSaved, setIsSaved] = useState(false)
  const [savePending, setSavePending] = useState(false)

  useEffect(() => {
    if (!id) return

    let cancelled = false
    setLoading(true)
    setError(null)

    Promise.all([fetchContentDetail(id), fetchOnboardingOptions()])
      .then(([detail, options]) => {
        if (cancelled) return
        setContent(detail)
        setIsSaved(detail.is_saved)
        setGoalLabels(new Map(options.goals.map((g) => [g.id, g.label])))
        setInterestLabels(new Map(options.interests.map((i) => [i.id, i.label])))
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
  }, [id])

  async function handleToggleSave() {
    if (!content) return
    setSavePending(true)
    try {
      if (isSaved) {
        await removeSavedContent(content.id)
        setIsSaved(false)
      } else {
        await saveContent(content.id)
        setIsSaved(true)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSavePending(false)
    }
  }

  if (loading) {
    return <p style={{ textAlign: 'center', marginTop: '4rem' }}>Loading...</p>
  }

  if (error || !content) {
    return (
      <div style={{ maxWidth: 640, margin: '3rem auto', padding: '0 1rem' }}>
        <p style={{ color: 'crimson' }}>{error ?? 'Content not found.'}</p>
        <Link to="/">← Back to your feed</Link>
      </div>
    )
  }

  const location = formatLocation(content.is_remote, content.location_city, content.location_country)
  const dateLine = formatDateLine(content.deadline, content.event_date)
  const recency = formatRecency(content.published_at)

  const matchedGoalLabels = content.matched_goal_ids
    .map((goalId) => goalLabels.get(goalId))
    .filter((label): label is string => Boolean(label))
  const matchedInterestLabels = content.matched_interest_ids
    .map((interestId) => interestLabels.get(interestId))
    .filter((label): label is string => Boolean(label))
  const hasMatches = matchedGoalLabels.length > 0 || matchedInterestLabels.length > 0

  return (
    <div style={{ maxWidth: 640, margin: '3rem auto', padding: '0 1rem' }}>
      <Link to="/">← Back to your feed</Link>

      <div style={{ marginTop: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.75rem', color: '#888', textTransform: 'uppercase' }}>
            {formatContentType(content.content_type)}
          </span>
          {recency && <span style={{ fontSize: '0.75rem', color: '#888' }}>{recency}</span>}
        </div>

        <h1 style={{ margin: '0.5rem 0' }}>{content.title}</h1>

        {content.organization && <p style={{ color: '#555', margin: '0.25rem 0' }}>{content.organization}</p>}

        {(location || dateLine) && (
          <div style={{ display: 'flex', gap: '1rem', fontSize: '0.9rem', color: '#555', margin: '0.5rem 0' }}>
            {location && <span>{location}</span>}
            {dateLine && <span>{dateLine}</span>}
          </div>
        )}

        {content.description && <p style={{ margin: '1rem 0', lineHeight: 1.5 }}>{content.description}</p>}

        {hasMatches && (
          <p style={{ margin: '1rem 0', fontSize: '0.9rem', color: '#2d6a4f' }}>
            Matches{' '}
            {matchedGoalLabels.length > 0 && <>your goal: {matchedGoalLabels.join(', ')}</>}
            {matchedGoalLabels.length > 0 && matchedInterestLabels.length > 0 && ' · '}
            {matchedInterestLabels.length > 0 && <>your interest: {matchedInterestLabels.join(', ')}</>}
          </p>
        )}

        <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem' }}>
          <button type="button" onClick={() => void handleToggleSave()} disabled={savePending}>
            {isSaved ? 'Saved' : 'Save'}
          </button>
          {content.url && (
            <a
              href={content.url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                padding: '0.4rem 0.9rem',
                border: '1px solid #333',
                borderRadius: 4,
                color: '#333',
                textDecoration: 'none',
              }}
            >
              {formatCtaLabel(content.content_type)} →
            </a>
          )}
        </div>
      </div>
    </div>
  )
}

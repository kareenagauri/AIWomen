import { useState } from 'react'
import { completeOnboarding, replaceMyInterests, type TagOption } from '../../lib/apiClient'

interface InterestsStepProps {
  options: TagOption[]
  initialSelectedIds: string[]
  onBack: () => void
  onFinish: (updatedInterests: TagOption[]) => void
}

export function InterestsStep({
  options,
  initialSelectedIds,
  onBack,
  onFinish,
}: InterestsStepProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set(initialSelectedIds))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  async function handleFinish() {
    if (selected.size === 0) {
      setError('Select at least one interest.')
      return
    }

    setError(null)
    setLoading(true)
    try {
      // Interests are saved first, then completion is requested — if
      // completion fails (e.g. a requirement regressed in another tab),
      // interests are still safely persisted and Finish is safe to retry.
      const updated = await replaceMyInterests(Array.from(selected))
      await completeOnboarding()
      onFinish(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      {options.map((interest) => (
        <label key={interest.id} style={{ display: 'block', marginBottom: '0.5rem' }}>
          <input
            type="checkbox"
            checked={selected.has(interest.id)}
            onChange={() => toggle(interest.id)}
          />{' '}
          {interest.label}
        </label>
      ))}
      {error && <p style={{ color: 'crimson', marginTop: '0.75rem' }}>{error}</p>}
      <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem' }}>
        <button type="button" onClick={onBack} disabled={loading}>
          Back
        </button>
        <button type="button" onClick={() => void handleFinish()} disabled={loading}>
          {loading ? 'Finishing...' : 'Finish'}
        </button>
      </div>
    </div>
  )
}

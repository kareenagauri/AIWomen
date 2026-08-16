import { useState } from 'react'
import { replaceMyGoals, type TagOption } from '../../lib/apiClient'

interface GoalsStepProps {
  options: TagOption[]
  initialSelectedIds: string[]
  onBack: () => void
  onNext: (updatedGoals: TagOption[]) => void
}

export function GoalsStep({ options, initialSelectedIds, onBack, onNext }: GoalsStepProps) {
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

  async function handleContinue() {
    if (selected.size === 0) {
      setError('Select at least one goal.')
      return
    }

    setError(null)
    setLoading(true)
    try {
      const updated = await replaceMyGoals(Array.from(selected))
      onNext(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      {options.map((goal) => (
        <label key={goal.id} style={{ display: 'block', marginBottom: '0.5rem' }}>
          <input type="checkbox" checked={selected.has(goal.id)} onChange={() => toggle(goal.id)} />{' '}
          {goal.label}
        </label>
      ))}
      {error && <p style={{ color: 'crimson', marginTop: '0.75rem' }}>{error}</p>}
      <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem' }}>
        <button type="button" onClick={onBack} disabled={loading}>
          Back
        </button>
        <button type="button" onClick={() => void handleContinue()} disabled={loading}>
          {loading ? 'Saving...' : 'Continue'}
        </button>
      </div>
    </div>
  )
}

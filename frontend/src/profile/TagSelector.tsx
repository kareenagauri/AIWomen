import type { TagOption } from '../lib/apiClient'

interface TagSelectorProps {
  label: string
  options: TagOption[]
  selectedIds: Set<string>
  onToggle: (id: string) => void
}

/** Purely presentational — no fetching, no apiClient/Supabase access.
 * Reused for both goals and interests on the profile page. */
export function TagSelector({ label, options, selectedIds, onToggle }: TagSelectorProps) {
  return (
    <fieldset style={{ border: 'none', padding: 0, margin: '1.25rem 0' }}>
      <legend style={{ fontWeight: 600, marginBottom: '0.5rem', padding: 0 }}>{label}</legend>
      {options.map((option) => (
        <label key={option.id} style={{ display: 'block', marginBottom: '0.5rem' }}>
          <input
            type="checkbox"
            checked={selectedIds.has(option.id)}
            onChange={() => onToggle(option.id)}
          />{' '}
          {option.label}
        </label>
      ))}
    </fieldset>
  )
}

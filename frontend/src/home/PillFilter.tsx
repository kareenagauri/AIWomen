interface PillFilterOption<T> {
  label: string
  value: T
}

interface PillFilterProps<T> {
  options: PillFilterOption<T>[]
  value: T
  onChange: (value: T) => void
}

/** Generic, presentational single-select pill list — no fetching, no
 * Supabase/apiClient access. Reused for content-type and location; the
 * existing CategoryFilter is left as-is and untouched. */
export function PillFilter<T>({ options, value, onChange }: PillFilterProps<T>) {
  return (
    <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
      {options.map((option) => {
        const isActive = value === option.value
        return (
          <button
            key={option.label}
            type="button"
            onClick={() => onChange(option.value)}
            style={{
              padding: '0.4rem 1rem',
              borderRadius: 999,
              border: '1px solid #333',
              backgroundColor: isActive ? '#333' : 'transparent',
              color: isActive ? '#fff' : '#333',
              cursor: 'pointer',
            }}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}

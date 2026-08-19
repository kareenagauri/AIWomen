type Category = 'career' | 'wellness' | undefined

interface CategoryFilterOption {
  label: string
  value: Category
}

const OPTIONS: CategoryFilterOption[] = [
  { label: 'All', value: undefined },
  { label: 'Career', value: 'career' },
  { label: 'Wellness', value: 'wellness' },
]

interface CategoryFilterProps {
  value: Category
  onChange: (category: Category) => void
}

export function CategoryFilter({ value, onChange }: CategoryFilterProps) {
  return (
    <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
      {OPTIONS.map((option) => {
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

import { useState, type FormEvent } from 'react'

interface SearchBarProps {
  initialValue?: string
  onSubmit: (term: string) => void
}

/** Presentational only — owns the in-progress input text, but never calls
 * an API, never touches Supabase/JWTs. Typing never triggers a request;
 * only submitting (Enter or the Search button, both handled by the
 * surrounding <form>) does. Submitting an empty/whitespace value is a
 * valid submission — the caller treats it as "clear the search filter". */
export function SearchBar({ initialValue = '', onSubmit }: SearchBarProps) {
  const [inputValue, setInputValue] = useState(initialValue)

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    onSubmit(inputValue.trim())
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
      <input
        type="search"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder="Search opportunities and resources..."
        style={{ flex: 1, padding: '0.4rem 0.6rem' }}
      />
      <button type="submit">Search</button>
    </form>
  )
}

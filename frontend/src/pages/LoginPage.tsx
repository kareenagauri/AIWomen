import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export function LoginPage() {
  const { signIn } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setLoading(true)

    const { error } = await signIn(email, password)

    setLoading(false)

    if (error) {
      setError(error)
      return
    }

    navigate('/')
  }

  return (
    <div style={{ maxWidth: 360, margin: '4rem auto' }}>
      <h1>Log in</h1>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="email">Email</label>
          <br />
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div style={{ marginTop: '0.75rem' }}>
          <label htmlFor="password">Password</label>
          <br />
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        {error && <p style={{ color: 'crimson', marginTop: '0.75rem' }}>{error}</p>}
        <button type="submit" disabled={loading} style={{ marginTop: '1rem' }}>
          {loading ? 'Logging in...' : 'Log in'}
        </button>
      </form>
      <p style={{ marginTop: '1rem' }}>
        Don&apos;t have an account? <Link to="/signup">Sign up</Link>
      </p>
    </div>
  )
}

import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export function SignupPage() {
  const { signUp } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [confirmationMessage, setConfirmationMessage] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setConfirmationMessage(null)

    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setLoading(true)
    const { error, needsEmailConfirmation } = await signUp(email, password)
    setLoading(false)

    if (error) {
      setError(error)
      return
    }

    if (needsEmailConfirmation) {
      setConfirmationMessage(
        'Account created. Check your email to confirm your address before logging in.',
      )
      return
    }

    // No confirmation required — Supabase already returned a session;
    // AuthContext will pick it up via onAuthStateChange.
    navigate('/')
  }

  return (
    <div style={{ maxWidth: 360, margin: '4rem auto' }}>
      <h1>Sign up</h1>
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
        <div style={{ marginTop: '0.75rem' }}>
          <label htmlFor="confirmPassword">Confirm password</label>
          <br />
          <input
            id="confirmPassword"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
          />
        </div>
        {error && <p style={{ color: 'crimson', marginTop: '0.75rem' }}>{error}</p>}
        {confirmationMessage && (
          <p style={{ color: 'green', marginTop: '0.75rem' }}>{confirmationMessage}</p>
        )}
        <button type="submit" disabled={loading} style={{ marginTop: '1rem' }}>
          {loading ? 'Signing up...' : 'Sign up'}
        </button>
      </form>
      <p style={{ marginTop: '1rem' }}>
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </div>
  )
}

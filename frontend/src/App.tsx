import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { fetchMe } from './lib/apiClient'
import { LoginPage } from './pages/LoginPage'
import { SignupPage } from './pages/SignupPage'

function HomePage() {
  const { user, signOut } = useAuth()
  const [meUserId, setMeUserId] = useState<string | null>(null)
  const [meError, setMeError] = useState<string | null>(null)

  useEffect(() => {
    fetchMe()
      .then((data) => setMeUserId(data.user_id))
      .catch((err) => setMeError(err instanceof Error ? err.message : String(err)))
  }, [])

  return (
    <div style={{ maxWidth: 480, margin: '4rem auto' }}>
      <h1>Authenticated</h1>
      <p>Signed in as: {user?.email}</p>
      <p>
        GET /api/me user_id:{' '}
        {meError ? (
          <span style={{ color: 'crimson' }}>{meError}</span>
        ) : (
          (meUserId ?? 'loading...')
        )}
      </p>
      <button onClick={() => signOut()}>Log out</button>
    </div>
  )
}

function AppRoutes() {
  const { session, loading } = useAuth()

  if (loading) {
    return <p style={{ textAlign: 'center', marginTop: '4rem' }}>Loading...</p>
  }

  return (
    <Routes>
      <Route path="/login" element={session ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route path="/signup" element={session ? <Navigate to="/" replace /> : <SignupPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <HomePage />
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}

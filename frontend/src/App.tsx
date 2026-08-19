import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { ContentDetailsPage } from './content/ContentDetailsPage'
import { SavedPage } from './content/SavedPage'
import { HomePage } from './home/HomePage'
import { ProfilePage } from './profile/ProfilePage'
import { OnboardingPage } from './onboarding/OnboardingPage'
import { OnboardingStatusProvider } from './onboarding/OnboardingStatusContext'
import { RedirectIfOnboarded } from './onboarding/RedirectIfOnboarded'
import { RequireOnboardingComplete } from './onboarding/RequireOnboardingComplete'
import { LoginPage } from './pages/LoginPage'
import { SignupPage } from './pages/SignupPage'

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
        path="/onboarding"
        element={
          <ProtectedRoute>
            <RedirectIfOnboarded>
              <OnboardingPage />
            </RedirectIfOnboarded>
          </ProtectedRoute>
        }
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <RequireOnboardingComplete>
              <HomePage />
            </RequireOnboardingComplete>
          </ProtectedRoute>
        }
      />
      <Route
        path="/content/:id"
        element={
          <ProtectedRoute>
            <RequireOnboardingComplete>
              <ContentDetailsPage />
            </RequireOnboardingComplete>
          </ProtectedRoute>
        }
      />
      <Route
        path="/saved"
        element={
          <ProtectedRoute>
            <RequireOnboardingComplete>
              <SavedPage />
            </RequireOnboardingComplete>
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <RequireOnboardingComplete>
              <ProfilePage />
            </RequireOnboardingComplete>
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
        <OnboardingStatusProvider>
          <AppRoutes />
        </OnboardingStatusProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

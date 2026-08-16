import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useOnboardingStatus } from './OnboardingStatusContext'

/** Gate for the main app: redirects to /onboarding if the user hasn't
 * finished it yet. Assumes it's rendered inside ProtectedRoute (session
 * already confirmed). */
export function RequireOnboardingComplete({ children }: { children: ReactNode }) {
  const { loading, onboardingCompleted } = useOnboardingStatus()

  if (loading) {
    return <p>Loading...</p>
  }

  if (!onboardingCompleted) {
    return <Navigate to="/onboarding" replace />
  }

  return <>{children}</>
}

import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useOnboardingStatus } from './OnboardingStatusContext'

/** Gate for /onboarding: redirects to "/" if the user already finished it,
 * so a completed user is never shown onboarding again. */
export function RedirectIfOnboarded({ children }: { children: ReactNode }) {
  const { loading, onboardingCompleted } = useOnboardingStatus()

  if (loading) {
    return <p>Loading...</p>
  }

  if (onboardingCompleted) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}

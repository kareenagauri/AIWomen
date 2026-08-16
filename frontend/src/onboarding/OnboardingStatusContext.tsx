import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import { useAuth } from '../auth/AuthContext'
import { fetchProfile } from '../lib/apiClient'

interface OnboardingStatusContextValue {
  loading: boolean
  onboardingCompleted: boolean | null
  /** Flips local state immediately after the final onboarding step succeeds,
   * so routing updates without waiting on a redundant re-fetch. */
  markCompleted: () => void
}

const OnboardingStatusContext = createContext<OnboardingStatusContextValue | undefined>(
  undefined,
)

export function OnboardingStatusProvider({ children }: { children: ReactNode }) {
  const { session } = useAuth()
  const [loading, setLoading] = useState(true)
  const [onboardingCompleted, setOnboardingCompleted] = useState<boolean | null>(null)

  const refresh = useCallback(async () => {
    if (!session) {
      setOnboardingCompleted(null)
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const profile = await fetchProfile()
      setOnboardingCompleted(profile.onboarding_completed)
    } finally {
      setLoading(false)
    }
  }, [session])

  useEffect(() => {
    void refresh()
  }, [refresh])

  function markCompleted() {
    setOnboardingCompleted(true)
  }

  return (
    <OnboardingStatusContext.Provider value={{ loading, onboardingCompleted, markCompleted }}>
      {children}
    </OnboardingStatusContext.Provider>
  )
}

export function useOnboardingStatus(): OnboardingStatusContextValue {
  const context = useContext(OnboardingStatusContext)
  if (!context) {
    throw new Error('useOnboardingStatus must be used within an OnboardingStatusProvider')
  }
  return context
}

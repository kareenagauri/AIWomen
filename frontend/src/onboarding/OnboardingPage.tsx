import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  fetchMyGoals,
  fetchMyInterests,
  fetchOnboardingOptions,
  fetchProfile,
  type OnboardingOptions,
  type Profile,
} from '../lib/apiClient'
import { useOnboardingStatus } from './OnboardingStatusContext'
import { StepProgress } from './StepProgress'
import { GoalsStep } from './steps/GoalsStep'
import { InterestsStep } from './steps/InterestsStep'
import { ProfileStep } from './steps/ProfileStep'

const TOTAL_STEPS = 3
const STEP_LABELS = ['About you', 'Your goals', 'Your interests']

function isProfileStepComplete(profile: Profile): boolean {
  return Boolean(
    profile.display_name?.trim() &&
      profile.career_field?.trim() &&
      profile.location_city?.trim() &&
      profile.location_country?.trim(),
  )
}

export function OnboardingPage() {
  const navigate = useNavigate()
  const { markCompleted } = useOnboardingStatus()

  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [profile, setProfile] = useState<Profile | null>(null)
  const [options, setOptions] = useState<OnboardingOptions | null>(null)
  const [selectedGoalIds, setSelectedGoalIds] = useState<string[]>([])
  const [selectedInterestIds, setSelectedInterestIds] = useState<string[]>([])
  const [currentStep, setCurrentStep] = useState(1)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const [profileData, goalsData, interestsData, optionsData] = await Promise.all([
          fetchProfile(),
          fetchMyGoals(),
          fetchMyInterests(),
          fetchOnboardingOptions(),
        ])

        if (cancelled) return

        setProfile(profileData)
        setOptions(optionsData)
        setSelectedGoalIds(goalsData.map((g) => g.id))
        setSelectedInterestIds(interestsData.map((i) => i.id))

        // Resume at the first incomplete step rather than always starting
        // over at Step 1 — this is what makes a refresh or return visit
        // safe: nothing above has to remember "where you were," it's
        // re-derived from what's actually saved on the server.
        if (!isProfileStepComplete(profileData)) {
          setCurrentStep(1)
        } else if (goalsData.length === 0) {
          setCurrentStep(2)
        } else {
          setCurrentStep(3)
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError(err instanceof Error ? err.message : String(err))
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [])

  if (loading) {
    return <p style={{ textAlign: 'center', marginTop: '4rem' }}>Loading...</p>
  }

  if (loadError || !profile || !options) {
    return (
      <p style={{ textAlign: 'center', marginTop: '4rem', color: 'crimson' }}>
        {loadError ?? 'Could not load onboarding data.'}
      </p>
    )
  }

  return (
    <div style={{ maxWidth: 480, margin: '4rem auto' }}>
      <StepProgress
        currentStep={currentStep}
        totalSteps={TOTAL_STEPS}
        label={STEP_LABELS[currentStep - 1]}
      />

      {currentStep === 1 && (
        <ProfileStep
          initialProfile={profile}
          onNext={(updated) => {
            setProfile(updated)
            setCurrentStep(2)
          }}
        />
      )}

      {currentStep === 2 && (
        <GoalsStep
          options={options.goals}
          initialSelectedIds={selectedGoalIds}
          onBack={() => setCurrentStep(1)}
          onNext={(updated) => {
            setSelectedGoalIds(updated.map((g) => g.id))
            setCurrentStep(3)
          }}
        />
      )}

      {currentStep === 3 && (
        <InterestsStep
          options={options.interests}
          initialSelectedIds={selectedInterestIds}
          onBack={() => setCurrentStep(2)}
          onFinish={(updated) => {
            setSelectedInterestIds(updated.map((i) => i.id))
            markCompleted()
            navigate('/')
          }}
        />
      )}
    </div>
  )
}

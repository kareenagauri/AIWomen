import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  fetchMyGoals,
  fetchMyInterests,
  fetchOnboardingOptions,
  fetchProfile,
  replaceMyGoals,
  replaceMyInterests,
  updateProfile,
  type Profile,
  type TagOption,
} from '../lib/apiClient'
import { TagSelector } from './TagSelector'

const SUCCESS_MESSAGE_DURATION_MS = 4000

function toggleId(set: Set<string>, id: string): Set<string> {
  const next = new Set(set)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  return next
}

export function ProfilePage() {
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  const [displayName, setDisplayName] = useState('')
  const [careerField, setCareerField] = useState('')
  const [city, setCity] = useState('')
  const [region, setRegion] = useState('')
  const [country, setCountry] = useState('')
  const [bio, setBio] = useState('')

  const [goalOptions, setGoalOptions] = useState<TagOption[]>([])
  const [interestOptions, setInterestOptions] = useState<TagOption[]>([])
  const [selectedGoalIds, setSelectedGoalIds] = useState<Set<string>>(new Set())
  const [selectedInterestIds, setSelectedInterestIds] = useState<Set<string>>(new Set())

  // Initial load: profile, current goals, current interests, and the
  // curated option lists — in parallel, all fetched fresh on every mount
  // (including a hard refresh), never from localStorage/URL/nav state.
  useEffect(() => {
    let cancelled = false

    Promise.all([fetchProfile(), fetchMyGoals(), fetchMyInterests(), fetchOnboardingOptions()])
      .then(([profile, goals, interests, options]) => {
        if (cancelled) return
        applyProfileToState(profile)
        setSelectedGoalIds(new Set(goals.map((g) => g.id)))
        setSelectedInterestIds(new Set(interests.map((i) => i.id)))
        setGoalOptions(options.goals)
        setInterestOptions(options.interests)
      })
      .catch((err) => {
        if (!cancelled) setLoadError(err instanceof Error ? err.message : String(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  // Success message auto-dismisses after a short duration — the simplest
  // option that satisfies "disappear naturally", nothing more elaborate.
  useEffect(() => {
    if (!saveSuccess) return
    const timer = setTimeout(() => setSaveSuccess(false), SUCCESS_MESSAGE_DURATION_MS)
    return () => clearTimeout(timer)
  }, [saveSuccess])

  function applyProfileToState(profile: Profile) {
    setDisplayName(profile.display_name ?? '')
    setCareerField(profile.career_field ?? '')
    setCity(profile.location_city ?? '')
    setRegion(profile.location_region ?? '')
    setCountry(profile.location_country ?? '')
    setBio(profile.bio ?? '')
  }

  // Same validation semantics as onboarding's ProfileStep — not extracted
  // into a shared function (it's a small, easy-to-eyeball predicate), but
  // deliberately worded identically rather than invented anew.
  const isValid =
    displayName.trim() !== '' &&
    careerField.trim() !== '' &&
    city.trim() !== '' &&
    country.trim() !== ''

  async function handleSave() {
    if (!isValid) {
      setSaveError('Display name, career field, city, and country are required.')
      setSaveSuccess(false)
      return
    }

    setSaveError(null)
    setSaveSuccess(false)
    setSaving(true)

    const [profileResult, goalsResult, interestsResult] = await Promise.allSettled([
      updateProfile({
        display_name: displayName.trim(),
        career_field: careerField.trim(),
        location_city: city.trim(),
        location_region: region.trim() || null,
        location_country: country.trim(),
        bio: bio.trim() || null,
      }),
      replaceMyGoals(Array.from(selectedGoalIds)),
      replaceMyInterests(Array.from(selectedInterestIds)),
    ])

    setSaving(false)

    const failedParts: string[] = []
    if (profileResult.status === 'rejected') failedParts.push('profile details')
    if (goalsResult.status === 'rejected') failedParts.push('goals')
    if (interestsResult.status === 'rejected') failedParts.push('interests')

    if (failedParts.length > 0) {
      setSaveError(
        `Could not save ${failedParts.join(', ')}. Your changes are still shown below — click Save Changes to retry.`,
      )
      return
    }

    // All three succeeded — re-sync local state from the confirmed server
    // values (idempotent PUTs, so this just reflects what's now persisted).
    if (profileResult.status === 'fulfilled') {
      applyProfileToState(profileResult.value)
    }
    if (goalsResult.status === 'fulfilled') {
      setSelectedGoalIds(new Set(goalsResult.value.map((g) => g.id)))
    }
    if (interestsResult.status === 'fulfilled') {
      setSelectedInterestIds(new Set(interestsResult.value.map((i) => i.id)))
    }

    setSaveSuccess(true)
  }

  if (loading) {
    return <p style={{ textAlign: 'center', marginTop: '4rem' }}>Loading profile...</p>
  }

  if (loadError) {
    return (
      <div style={{ maxWidth: 640, margin: '3rem auto', padding: '0 1rem' }}>
        <p style={{ color: 'crimson' }}>{loadError}</p>
        <Link to="/">← Back to your feed</Link>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 640, margin: '3rem auto', padding: '0 1rem' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          marginBottom: '1.5rem',
        }}
      >
        <h1 style={{ margin: 0 }}>Profile</h1>
        <Link to="/">← Back to your feed</Link>
      </div>

      <div>
        <label htmlFor="displayName">Display name *</label>
        <br />
        <input id="displayName" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
      </div>
      <div style={{ marginTop: '0.75rem' }}>
        <label htmlFor="careerField">Career field *</label>
        <br />
        <input id="careerField" value={careerField} onChange={(e) => setCareerField(e.target.value)} />
      </div>
      <div style={{ marginTop: '0.75rem' }}>
        <label htmlFor="city">City *</label>
        <br />
        <input id="city" value={city} onChange={(e) => setCity(e.target.value)} />
      </div>
      <div style={{ marginTop: '0.75rem' }}>
        <label htmlFor="region">Region / state (optional)</label>
        <br />
        <input id="region" value={region} onChange={(e) => setRegion(e.target.value)} />
      </div>
      <div style={{ marginTop: '0.75rem' }}>
        <label htmlFor="country">Country *</label>
        <br />
        <input id="country" value={country} onChange={(e) => setCountry(e.target.value)} />
      </div>
      <div style={{ marginTop: '0.75rem' }}>
        <label htmlFor="bio">Short bio (optional)</label>
        <br />
        <textarea id="bio" value={bio} onChange={(e) => setBio(e.target.value)} rows={3} />
      </div>

      <TagSelector
        label="Goals"
        options={goalOptions}
        selectedIds={selectedGoalIds}
        onToggle={(id) => setSelectedGoalIds((prev) => toggleId(prev, id))}
      />
      <TagSelector
        label="Interests"
        options={interestOptions}
        selectedIds={selectedInterestIds}
        onToggle={(id) => setSelectedInterestIds((prev) => toggleId(prev, id))}
      />

      {saveError && <p style={{ color: 'crimson', marginTop: '1rem' }}>{saveError}</p>}
      {saveSuccess && <p style={{ color: 'green', marginTop: '1rem' }}>Changes saved successfully.</p>}

      <button type="button" onClick={() => void handleSave()} disabled={saving} style={{ marginTop: '1rem' }}>
        {saving ? 'Saving...' : 'Save Changes'}
      </button>
    </div>
  )
}

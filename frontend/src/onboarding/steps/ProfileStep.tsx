import { useState, type FormEvent } from 'react'
import { updateProfile, type Profile } from '../../lib/apiClient'

interface ProfileStepProps {
  initialProfile: Profile
  onNext: (updatedProfile: Profile) => void
}

export function ProfileStep({ initialProfile, onNext }: ProfileStepProps) {
  const [displayName, setDisplayName] = useState(initialProfile.display_name ?? '')
  const [careerField, setCareerField] = useState(initialProfile.career_field ?? '')
  const [city, setCity] = useState(initialProfile.location_city ?? '')
  const [region, setRegion] = useState(initialProfile.location_region ?? '')
  const [country, setCountry] = useState(initialProfile.location_country ?? '')
  const [bio, setBio] = useState(initialProfile.bio ?? '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isValid =
    displayName.trim() !== '' &&
    careerField.trim() !== '' &&
    city.trim() !== '' &&
    country.trim() !== ''

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()

    if (!isValid) {
      setError('Display name, career field, city, and country are required.')
      return
    }

    setError(null)
    setLoading(true)
    try {
      const updated = await updateProfile({
        display_name: displayName.trim(),
        career_field: careerField.trim(),
        location_city: city.trim(),
        location_region: region.trim() || null,
        location_country: country.trim(),
        bio: bio.trim() || null,
      })
      onNext(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label htmlFor="displayName">Display name *</label>
        <br />
        <input
          id="displayName"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          required
        />
      </div>
      <div style={{ marginTop: '0.75rem' }}>
        <label htmlFor="careerField">Career field *</label>
        <br />
        <input
          id="careerField"
          value={careerField}
          onChange={(e) => setCareerField(e.target.value)}
          required
        />
      </div>
      <div style={{ marginTop: '0.75rem' }}>
        <label htmlFor="city">City *</label>
        <br />
        <input id="city" value={city} onChange={(e) => setCity(e.target.value)} required />
      </div>
      <div style={{ marginTop: '0.75rem' }}>
        <label htmlFor="region">Region / state (optional)</label>
        <br />
        <input id="region" value={region} onChange={(e) => setRegion(e.target.value)} />
      </div>
      <div style={{ marginTop: '0.75rem' }}>
        <label htmlFor="country">Country *</label>
        <br />
        <input
          id="country"
          value={country}
          onChange={(e) => setCountry(e.target.value)}
          required
        />
      </div>
      <div style={{ marginTop: '0.75rem' }}>
        <label htmlFor="bio">Short bio (optional)</label>
        <br />
        <textarea id="bio" value={bio} onChange={(e) => setBio(e.target.value)} rows={3} />
      </div>
      {error && <p style={{ color: 'crimson', marginTop: '0.75rem' }}>{error}</p>}
      <div style={{ marginTop: '1rem' }}>
        <button type="submit" disabled={loading || !isValid}>
          {loading ? 'Saving...' : 'Continue'}
        </button>
      </div>
    </form>
  )
}

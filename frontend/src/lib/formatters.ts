/** Pure display-formatting helpers, shared across the home feed and content
 * details page. No fetching, no business/scoring logic — purely
 * presentation of already-fetched data. */

export function formatContentType(contentType: string): string {
  return contentType
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

export function formatLocation(
  isRemote: boolean,
  city: string | null,
  country: string | null,
): string | null {
  if (isRemote) return 'Remote'
  if (city) return country ? `${city}, ${country}` : city
  return null
}

function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function formatDateLine(deadline: string | null, eventDate: string | null): string | null {
  if (deadline) return `Apply by ${formatDate(deadline)}`
  if (eventDate) return `Event on ${formatDate(eventDate)}`
  return null
}

/** Returns a short relative-recency string for items published within the
 * last 30 days, or null otherwise — display only, not the scoring rule. */
export function formatRecency(publishedAt: string | null): string | null {
  if (!publishedAt) return null

  const diffMs = Date.now() - new Date(publishedAt).getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays <= 0) return 'Posted today'
  if (diffDays === 1) return 'Posted 1 day ago'
  if (diffDays <= 30) return `Posted ${diffDays} days ago`
  return null
}

/** Truncates text to at most maxLength characters, cutting back to the
 * last whitespace boundary rather than mid-word, and appending "...".
 * Text already within maxLength is returned unchanged. Display only —
 * never mutates the underlying data the caller holds. */
export function truncateDescription(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text

  const cut = text.slice(0, maxLength)
  const lastSpace = cut.lastIndexOf(' ')
  const safeCut = lastSpace > 0 ? cut.slice(0, lastSpace) : cut

  return `${safeCut}...`
}

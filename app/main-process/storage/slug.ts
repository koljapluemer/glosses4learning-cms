/**
 * CRITICAL: Exact port of Python slug generation
 */
export function deriveSlug(text: string): string {
  if (!text) {
    throw new Error('Content must produce a valid slug.')
  }

  // ONLY remove actually illegal characters and trim to reasonable length
  // do NOT remove punctuation, spaces or anything else
  let slug = text.replace(/[/\\?*:|"<>]/g, '')
  slug = slug.replace(/[\x00-\x1F]/g, '')

  if (slug.length > 120) {
    slug = slug.substring(0, 120).replace(/[\s.]+$/g, '')
  }

  if (!slug) {
    throw new Error('Content must produce a valid slug.')
  }

  return slug
}

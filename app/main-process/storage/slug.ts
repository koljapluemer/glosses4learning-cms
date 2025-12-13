/**
 * CRITICAL: Exact port of Python slug generation
 */
export function deriveSlug(text: string): string {
  if (!text) {
    throw new Error('Content must produce a valid slug.')
  }

  let slug = text.replace(/[/\\?*:|"<>]/g, '')
  slug = slug.replace(/[\x00-\x1F]/g, '')
  slug = slug.replace(/[\s.]+$/g, '')

  if (slug.length > 120) {
    slug = slug.substring(0, 120).replace(/[\s.]+$/g, '')
  }

  if (!slug) {
    throw new Error('Content must produce a valid slug.')
  }

  return slug
}

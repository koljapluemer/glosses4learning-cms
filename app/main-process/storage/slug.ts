/**
 * CRITICAL: Exact port of Python slug generation from src/shared/storage.py:61-77
 *
 * Build a filesystem-safe slug while preserving Unicode.
 * - Remove characters illegal on common filesystems: / \ ? * : | " < >
 * - Remove control chars (ord < 32)
 * - Trim trailing dot/space (Windows)
 * - Truncate to a safe length (120 chars)
 */
export function deriveSlug(text: string): string {
  if (!text) {
    throw new Error('Content must produce a valid slug.')
  }

  // Remove illegal filesystem chars: / \ ? * : | " < >
  let slug = text.replace(/[/\\?*:|"<>]/g, '')

  // Remove control chars (ord < 32, i.e., \x00-\x1F)
  slug = slug.replace(/[\x00-\x1F]/g, '')

  // Trim trailing spaces and dots (Windows filesystem requirement)
  slug = slug.replace(/[ .]+$/g, '')

  // Truncate to 120 chars, then re-trim trailing spaces and dots
  if (slug.length > 120) {
    slug = slug.substring(0, 120).replace(/[ .]+$/g, '')
  }

  if (!slug) {
    throw new Error('Content must produce a valid slug.')
  }

  return slug
}

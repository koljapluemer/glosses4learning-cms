/**
 * Build a filesystem-safe slug while preserving Unicode.
 *
 * CRITICAL: This is the single source of truth for slug generation.
 * Must match Python implementation exactly (src/shared/storage.py:61-77).
 *
 * - Remove characters illegal on common filesystems: / \ ? * : | " < >
 * - Remove control chars (ASCII < 32)
 * - Trim trailing dot/space (Windows)
 * - Truncate to safe length (120 chars)
 *
 * @param text - The text to convert to a slug
 * @returns The slugified text
 * @throws Error if the result is empty
 */
export function deriveSlug(text: string): string {
  if (!text) {
    throw new Error('Content must produce a valid slug.')
  }

  // Remove filesystem-illegal chars: / \ ? * : | " < >
  let slug = text.replace(/[/\\?*:|"<>]/g, '')

  // Remove control characters (chars with code < 32)
  slug = slug.replace(/[\x00-\x1F]/g, '')

  // Trim trailing dots and spaces (Windows compatibility)
  slug = slug.replace(/[\s.]+$/g, '')

  // Truncate to 120 chars
  if (slug.length > 120) {
    slug = slug.substring(0, 120)
    // Trim trailing dots and spaces again after truncation
    slug = slug.replace(/[\s.]+$/g, '')
  }

  if (!slug) {
    throw new Error('Content must produce a valid slug.')
  }

  return slug
}

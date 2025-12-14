/**
 * Common gloss manipulation operations
 * Port of src/shared/gloss_operations.py:10-104
 */

import type { Gloss } from './types'
import type { GlossStorage } from './fsGlossStorage'

/**
 * Attach translation to gloss with optional note
 *
 * Creates a bidirectional translation relationship and optionally
 * attaches a one-way note to the translation gloss.
 *
 * Python ref: src/shared/gloss_operations.py:10-59
 *
 * @param storage - GlossStorage instance
 * @param sourceGloss - Source gloss to translate from
 * @param translationText - Translation text in target language
 * @param translationLanguage - Target language code
 * @param noteText - Optional note text in native language
 * @param noteLanguage - Language code for the note (typically native language)
 * @returns The created/found translation gloss
 *
 * @example
 * const translation = attachTranslationWithNote(
 *   storage,
 *   nativeGloss,
 *   "Danke",
 *   "deu",
 *   "informal",
 *   "eng"
 * )
 */
export function attachTranslationWithNote(
  storage: GlossStorage,
  sourceGloss: Gloss,
  translationText: string,
  translationLanguage: string,
  noteText: string | null,
  noteLanguage: string
): Gloss {
  // Create or find translation gloss
  const translationGloss = storage.ensureGloss(translationLanguage, translationText)

  // Bidirectional translation relation
  storage.attachRelation(sourceGloss, 'translations', translationGloss)
  storage.attachRelation(translationGloss, 'translations', sourceGloss)

  // One-way note relation (if note exists)
  // Note is in native language, attached TO the target translation
  if (noteText && noteText.trim()) {
    const noteGloss = storage.ensureGloss(noteLanguage, noteText.trim())
    storage.attachRelation(translationGloss, 'notes', noteGloss)
  }

  return translationGloss
}

/**
 * Add a log marker to a gloss
 *
 * Used for marking glosses with special states like:
 * - SPLIT_CONSIDERED_UNNECESSARY
 * - TRANSLATION_CONSIDERED_IMPOSSIBLE:{language}
 * - USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE:{language}
 *
 * The log entry is timestamped with UTC ISO format to track when
 * the decision was made. This prevents the agent from repeatedly
 * attempting impossible operations.
 *
 * Python ref: src/shared/gloss_operations.py:62-104
 *
 * @param storage - GlossStorage instance
 * @param glossRef - Gloss reference in format "language:slug"
 * @param marker - Log marker string to add
 * @throws Error if gloss not found
 *
 * @example
 * markGlossLog(storage, "arb:؟", "TRANSLATION_CONSIDERED_IMPOSSIBLE:eng")
 * markGlossLog(storage, "spa:sal", "SPLIT_CONSIDERED_UNNECESSARY")
 */
export function markGlossLog(
  storage: GlossStorage,
  glossRef: string,
  marker: string
): void {
  const gloss = storage.resolveReference(glossRef)
  if (!gloss) {
    throw new Error(`Gloss not found: ${glossRef}`)
  }

  // Ensure logs is a dict, not undefined or other type
  const logs = gloss.logs && typeof gloss.logs === 'object' ? gloss.logs : {}

  // Add timestamped marker
  const timestamp = new Date().toISOString()
  logs[timestamp] = marker

  // Save updated gloss
  gloss.logs = logs
  storage.saveGloss(gloss)
}

/**
 * Language entity types
 * Ported from src/schema/language.schema.json
 */

export interface Language {
  isoCode: string      // ISO 639-3 code (e.g., 'eng', 'spa')
  displayName: string  // e.g., 'English', 'Spanish'
  symbol: string       // e.g., 'EN', '🇲🇽'
  aiNote?: string      // Optional hint for LLM about this language
}

/**
 * Language loader utilities
 * Ported from src/shared/languages.py:11-25
 */

import type { Language } from './types'

let languageCache: Language[] | null = null

/**
 * Load all available languages from the backend
 * Results are cached for performance
 */
export async function loadLanguages(): Promise<Language[]> {
  if (languageCache) {
    return languageCache
  }

  try {
    const languages = await window.electronAPI.language.list()
    languageCache = languages
    return languages
  } catch (error) {
    console.error('Failed to load languages:', error)
    return []
  }
}

/**
 * Get the symbol/flag for a language by ISO code
 */
export function getLanguageSymbol(isoCode: string, languages: Language[]): string {
  const language = languages.find(l => l.isoCode === isoCode)
  return language?.symbol || isoCode.toUpperCase()
}

/**
 * Clear the language cache (useful for testing)
 */
export function clearLanguageCache(): void {
  languageCache = null
}

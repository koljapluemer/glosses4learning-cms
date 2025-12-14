/**
 * Settings store for global app settings
 * Ported from src/shared/state.py:8-32
 *
 * Uses Vue 3 reactivity with electron-store persistence via IPC
 */

import { ref, type Ref } from 'vue'

export interface AppSettings {
  nativeLanguage: string | null  // ISO code for learner's native language
  targetLanguage: string | null  // ISO code for language being learned
  lastSituationRef: string | null // Format: "language:slug"
  openaiApiKey: string | null     // OpenAI API key for AI features
}

const settings: Ref<AppSettings> = ref({
  nativeLanguage: null,
  targetLanguage: null,
  lastSituationRef: null,
  openaiApiKey: null
})

let initialized = false

/**
 * Initialize settings from electron-store
 * Call this once on app boot before using settings
 */
export async function initSettings(): Promise<void> {
  if (initialized) {
    return
  }

  try {
    const native = await window.electronAPI.settings.get<string>('nativeLanguage')
    const target = await window.electronAPI.settings.get<string>('targetLanguage')
    const lastSit = await window.electronAPI.settings.get<string>('lastSituationRef')
    const apiKey = await window.electronAPI.settings.get<string>('openaiApiKey')

    settings.value = {
      nativeLanguage: native || null,
      targetLanguage: target || null,
      lastSituationRef: lastSit || null,
      openaiApiKey: apiKey || null
    }

    initialized = true
  } catch (error) {
    console.error('Failed to initialize settings:', error)
    // Keep defaults on error
  }
}

/**
 * Vue composable for accessing and updating settings
 */
export function useSettings() {
  return {
    /** Reactive settings object */
    settings,

    /** Set the native (learner's) language */
    async setNativeLanguage(isoCode: string): Promise<void> {
      settings.value.nativeLanguage = isoCode
      await window.electronAPI.settings.set('nativeLanguage', isoCode)
    },

    /** Set the target (learning) language */
    async setTargetLanguage(isoCode: string): Promise<void> {
      settings.value.targetLanguage = isoCode
      await window.electronAPI.settings.set('targetLanguage', isoCode)
    },

    /** Set the last opened situation */
    async setLastSituation(ref: string): Promise<void> {
      settings.value.lastSituationRef = ref
      await window.electronAPI.settings.set('lastSituationRef', ref)
    },

    /** Set the OpenAI API key */
    async setOpenAIApiKey(key: string): Promise<void> {
      settings.value.openaiApiKey = key
      await window.electronAPI.settings.set('openaiApiKey', key)
    },

    /** Clear all settings (useful for testing/reset) */
    async clearSettings(): Promise<void> {
      settings.value = {
        nativeLanguage: null,
        targetLanguage: null,
        lastSituationRef: null,
        openaiApiKey: null
      }
      await window.electronAPI.settings.set('nativeLanguage', null)
      await window.electronAPI.settings.set('targetLanguage', null)
      await window.electronAPI.settings.set('lastSituationRef', null)
      await window.electronAPI.settings.set('openaiApiKey', null)
    }
  }
}

import { contextBridge, ipcRenderer } from 'electron'
import type { Gloss, UsageInfo } from './main-process/storage/types'

interface Language {
  isoCode: string
  displayName: string
  symbol: string
  aiNote?: string
}

interface ExportResult {
  success: boolean
  message: string
}

interface DeleteResult {
  success: boolean
  message: string
  refsRemoved: number
}

export type ElectronAPI = {
  gloss: {
    load: (language: string, slug: string) => Promise<Gloss | null>
    save: (gloss: Gloss) => Promise<void>
    ensure: (language: string, content: string) => Promise<Gloss>
    delete: (language: string, slug: string) => Promise<void>
    resolveRef: (ref: string) => Promise<Gloss>
    attachRelation: (baseRef: string, field: string, targetRef: string) => Promise<void>
    detachRelation: (baseRef: string, field: string, targetRef: string) => Promise<void>
    updateContent: (ref: string, newContent: string) => Promise<void>
    checkReferences: (ref: string) => Promise<UsageInfo>
    list: (language?: string) => Promise<Gloss[]>
    deleteWithCleanup: (language: string, slug: string) => Promise<DeleteResult>
    findByTag: (tagRef: string, limit?: number) => Promise<Gloss[]>
    searchByContent: (language: string, substring: string, limit?: number) => Promise<Gloss[]>
    attachTranslationWithNote: (
      sourceRef: string,
      translationText: string,
      translationLanguage: string,
      noteText: string | null,
      noteLanguage: string
    ) => Promise<Gloss>
    markLog: (glossRef: string, marker: string) => Promise<void>
    noteUsageCount: (noteRef: string) => Promise<{ count: number; parents: string[] }>
    evaluateGoalState: (
      glossRef: string,
      nativeLanguage: string,
      targetLanguage: string
    ) => Promise<{ state: 'red' | 'yellow' | 'green'; log: string }>
  }
  language: {
    list: () => Promise<Language[]>
  }
  situation: {
    list: (query?: string) => Promise<Gloss[]>
    create: (content: string) => Promise<Gloss>
    export: () => Promise<ExportResult>
  }
  settings: {
    get: <T>(key: string) => Promise<T | undefined>
    set: (key: string, value: unknown) => Promise<void>
  }
  aiLog: {
    write: (entry: { action: string; refs?: string[]; payload?: Record<string, unknown> }) => Promise<void>
  }
}

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
const api: ElectronAPI = {
  gloss: {
    load: (language, slug) => ipcRenderer.invoke('gloss:load', language, slug),
    save: (gloss) => ipcRenderer.invoke('gloss:save', gloss),
    ensure: (language, content) => ipcRenderer.invoke('gloss:ensure', language, content),
    delete: (language, slug) => ipcRenderer.invoke('gloss:delete', language, slug),
    resolveRef: (ref) => ipcRenderer.invoke('gloss:resolveRef', ref),
    attachRelation: (baseRef, field, targetRef) =>
      ipcRenderer.invoke('gloss:attachRelation', baseRef, field, targetRef),
    detachRelation: (baseRef, field, targetRef) =>
      ipcRenderer.invoke('gloss:detachRelation', baseRef, field, targetRef),
    updateContent: (ref, newContent) =>
      ipcRenderer.invoke('gloss:updateContent', ref, newContent),
    checkReferences: (ref) => ipcRenderer.invoke('gloss:checkReferences', ref),
    list: (language) => ipcRenderer.invoke('gloss:list', language),
    deleteWithCleanup: (language, slug) =>
      ipcRenderer.invoke('gloss:deleteWithCleanup', language, slug),
    findByTag: (tagRef, limit) => ipcRenderer.invoke('gloss:findByTag', tagRef, limit),
    searchByContent: (language, substring, limit) =>
      ipcRenderer.invoke('gloss:searchByContent', language, substring, limit),
    attachTranslationWithNote: (sourceRef, translationText, translationLanguage, noteText, noteLanguage) =>
      ipcRenderer.invoke(
        'gloss:attachTranslationWithNote',
        sourceRef,
        translationText,
        translationLanguage,
        noteText,
        noteLanguage
      ),
    markLog: (glossRef, marker) => ipcRenderer.invoke('gloss:markLog', glossRef, marker),
    noteUsageCount: (noteRef) => ipcRenderer.invoke('gloss:noteUsageCount', noteRef),
    evaluateGoalState: (glossRef, nativeLanguage, targetLanguage) =>
      ipcRenderer.invoke('gloss:evaluateGoalState', glossRef, nativeLanguage, targetLanguage)
  },
  language: {
    list: () => ipcRenderer.invoke('language:list')
  },
  situation: {
    list: (query) => ipcRenderer.invoke('situation:list', query),
    create: (content) => ipcRenderer.invoke('situation:create', content),
    export: () => ipcRenderer.invoke('situation:export')
  },
  settings: {
    get: (key) => ipcRenderer.invoke('settings:get', key),
    set: (key, value) => ipcRenderer.invoke('settings:set', key, value)
  },
  aiLog: {
    write: (entry) => ipcRenderer.invoke('ai-log:write', entry)
  }
}

contextBridge.exposeInMainWorld('electronAPI', api)

declare global {
  interface Window {
    electronAPI: ElectronAPI
  }
}

import { contextBridge, ipcRenderer } from 'electron'

export type ElectronAPI = {
  gloss: {
    load: (language: string, slug: string) => Promise<any>
    save: (gloss: any) => Promise<void>
    ensure: (language: string, content: string) => Promise<any>
    delete: (language: string, slug: string) => Promise<void>
    resolveRef: (ref: string) => Promise<any>
    attachRelation: (baseRef: string, field: string, targetRef: string) => Promise<void>
    detachRelation: (baseRef: string, field: string, targetRef: string) => Promise<void>
    updateContent: (ref: string, newContent: string) => Promise<void>
    checkReferences: (ref: string) => Promise<any>
    list: (language?: string) => Promise<any[]>
  }
  language: {
    list: () => Promise<any[]>
  }
  situation: {
    list: (query?: string) => Promise<any[]>
    create: (content: string) => Promise<any>
    export: () => Promise<any>
  }
  settings: {
    get: <T>(key: string) => Promise<T | undefined>
    set: (key: string, value: unknown) => Promise<void>
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
    list: (language) => ipcRenderer.invoke('gloss:list', language)
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
  }
}

contextBridge.exposeInMainWorld('electronAPI', api)

declare global {
  interface Window {
    electronAPI: ElectronAPI
  }
}

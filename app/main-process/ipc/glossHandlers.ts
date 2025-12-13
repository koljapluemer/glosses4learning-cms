import { ipcMain } from 'electron'
import path from 'path'
import { GlossStorage } from '../storage/fsGlossStorage'
import type { Gloss, UsageInfo } from '../storage/types'
import { RELATIONSHIP_FIELDS } from '../storage/relationRules'

// Initialize storage with data/ and situations/ paths
const dataRoot = path.join(process.cwd(), 'data')
const situationsRoot = path.join(process.cwd(), 'situations')
const storage = new GlossStorage(dataRoot, situationsRoot)

export function setupGlossHandlers() {
  ipcMain.handle('gloss:load', async (_, language: string, slug: string) => {
    return storage.loadGloss(language, slug)
  })

  ipcMain.handle('gloss:save', async (_, gloss: Gloss) => {
    storage.saveGloss(gloss)
  })

  ipcMain.handle('gloss:ensure', async (_, language: string, content: string) => {
    return storage.ensureGloss(language, content)
  })

  ipcMain.handle('gloss:delete', async (_, language: string, slug: string) => {
    storage.deleteGloss(language, slug)
  })

  ipcMain.handle('gloss:resolveRef', async (_, ref: string) => {
    return storage.resolveReference(ref)
  })

  ipcMain.handle(
    'gloss:attachRelation',
    async (_, baseRef: string, field: string, targetRef: string) => {
      const base = storage.resolveReference(baseRef)
      const target = storage.resolveReference(targetRef)

      if (!base || !target) {
        throw new Error('Base or target gloss not found')
      }

      if (!RELATIONSHIP_FIELDS.includes(field as any)) {
        throw new Error(`Invalid relationship field: ${field}`)
      }

      storage.attachRelation(base, field as any, target)
    }
  )

  ipcMain.handle(
    'gloss:detachRelation',
    async (_, baseRef: string, field: string, targetRef: string) => {
      const base = storage.resolveReference(baseRef)

      if (!base) {
        throw new Error('Base gloss not found')
      }

      if (!RELATIONSHIP_FIELDS.includes(field as any)) {
        throw new Error(`Invalid relationship field: ${field}`)
      }

      storage.detachRelation(base, field as any, targetRef)
    }
  )

  ipcMain.handle('gloss:updateContent', async (_, ref: string, newContent: string) => {
    const gloss = storage.resolveReference(ref)
    if (!gloss) {
      throw new Error('Gloss not found')
    }

    const oldRef = ref
    gloss.content = newContent

    // This will create a new file with the new slug if content changed
    storage.createGloss(gloss)

    // Delete old file if slug changed
    const parts = oldRef.split(':')
    const oldSlug = parts.slice(1).join(':')
    if (oldSlug !== gloss.slug) {
      storage.deleteGloss(gloss.language, oldSlug)
    }
  })

  ipcMain.handle('gloss:checkReferences', async (_, ref: string) => {
    const usage: UsageInfo = {
      usedAsPart: [],
      usedAsUsageExample: [],
      usedAsTranslation: []
    }

    const allGlosses = storage.listGlosses()

    for (const gloss of allGlosses) {
      const glossRef = `${gloss.language}:${gloss.slug}`

      if (gloss.parts?.includes(ref)) {
        usage.usedAsPart.push(glossRef)
      }
      if (gloss.usage_examples?.includes(ref)) {
        usage.usedAsUsageExample.push(glossRef)
      }
      if (gloss.translations?.includes(ref)) {
        usage.usedAsTranslation.push(glossRef)
      }
    }

    return usage
  })

  ipcMain.handle('gloss:list', async (_, language?: string) => {
    return storage.listGlosses(language)
  })
}

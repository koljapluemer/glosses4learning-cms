import { ipcMain } from 'electron'
import path from 'path'
import { GlossStorage } from '../storage/fsGlossStorage'
import type { Gloss, UsageInfo } from '../storage/types'
import { RELATIONSHIP_FIELDS, type RelationshipField } from '../storage/relationRules'
import { attachTranslationWithNote, markGlossLog } from '../storage/glossOperations'

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

      if (!RELATIONSHIP_FIELDS.includes(field as RelationshipField)) {
        throw new Error(`Invalid relationship field: ${field}`)
      }

      storage.attachRelation(base, field as RelationshipField, target)
    }
  )

  ipcMain.handle(
    'gloss:detachRelation',
    async (_, baseRef: string, field: string, targetRef: string) => {
      const base = storage.resolveReference(baseRef)

      if (!base) {
        throw new Error('Base gloss not found')
      }

      if (!RELATIONSHIP_FIELDS.includes(field as RelationshipField)) {
        throw new Error(`Invalid relationship field: ${field}`)
      }

      storage.detachRelation(base, field as RelationshipField, targetRef)
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
    const updated = storage.createGloss(gloss)

    // If slug changed, rewrite references across all glosses before deleting old file
    const oldSlug = oldRef.split(':').slice(1).join(':')
    const newSlug = updated.slug
    const newRef = `${updated.language}:${newSlug}`

    if (oldSlug !== newSlug) {
      const oldRefCanonical = `${updated.language}:${oldSlug}`
      for (const item of storage.iterateAllGlosses()) {
        let changed = false
        const record = item as Record<string, string[]>
        for (const field of RELATIONSHIP_FIELDS) {
          const vals = record[field] || []
          const replaced = vals.map((v: string) => (v === oldRefCanonical ? newRef : v))
          if (replaced.some((v, idx) => v !== vals[idx])) {
            record[field] = replaced
            changed = true
          }
        }
        if (changed) {
          storage.saveGloss(item)
        }
      }
      storage.deleteGloss(updated.language, oldSlug)
    }
  })

  ipcMain.handle('gloss:checkReferences', async (_, ref: string) => {
    const usage: UsageInfo = {
      usedAsPart: [],
      usedAsUsageExample: [],
      usedAsTranslation: []
    }

    // CRITICAL FIX: Use lazy iteration instead of loading all glosses into memory
    for (const gloss of storage.iterateAllGlosses()) {
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

  // New handlers for Phase 1 storage improvements
  ipcMain.handle(
    'gloss:deleteWithCleanup',
    async (_, language: string, slug: string) => {
      return storage.deleteGlossWithCleanup(language, slug)
    }
  )

  ipcMain.handle('gloss:findByTag', async (_, tagRef: string, limit: number = 100) => {
    const results: Gloss[] = []
    for (const gloss of storage.findGlossesByTag(tagRef)) {
      results.push(gloss)
      if (results.length >= limit) break // Prevent unbounded results
    }
    return results
  })

  ipcMain.handle(
    'gloss:searchByContent',
    async (_, language: string, substring: string, limit: number = 50) => {
      const results: Gloss[] = []
      for (const gloss of storage.searchGlossesByContent(language, substring)) {
        results.push(gloss)
        if (results.length >= limit) break
      }
      return results
    }
  )

  ipcMain.handle(
    'gloss:attachTranslationWithNote',
    async (
      _,
      sourceRef: string,
      translationText: string,
      translationLanguage: string,
      noteText: string | null,
      noteLanguage: string
    ) => {
      const sourceGloss = storage.resolveReference(sourceRef)
      if (!sourceGloss) {
        throw new Error('Source gloss not found')
      }

      return attachTranslationWithNote(
        storage,
        sourceGloss,
        translationText,
        translationLanguage,
        noteText,
        noteLanguage
      )
    }
  )

  ipcMain.handle('gloss:markLog', async (_, glossRef: string, marker: string) => {
    markGlossLog(storage, glossRef, marker)
  })

  ipcMain.handle('gloss:noteUsageCount', async (_, noteRef: string) => {
    let count = 0
    const parents: string[] = []
    for (const gloss of storage.iterateAllGlosses()) {
      const notes = gloss.notes || []
      if (notes.includes(noteRef)) {
        count += 1
        parents.push(`${gloss.language}:${gloss.slug}`)
      }
    }
    return { count, parents }
  })

  ipcMain.handle(
    'gloss:evaluateGoalState',
    async (_, glossRef: string, nativeLanguage: string, targetLanguage: string) => {
      const gloss = storage.resolveReference(glossRef)
      if (!gloss) {
        throw new Error('Gloss not found')
      }

      // Import goal state evaluation
      const { evaluateGoalState } = await import('../storage/goalStateEval')
      return evaluateGoalState(gloss, storage, nativeLanguage, targetLanguage)
    }
  )
}

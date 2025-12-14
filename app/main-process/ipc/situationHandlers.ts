import { ipcMain } from 'electron'
import path from 'path'
import { GlossStorage } from '../storage/fsGlossStorage'
import type { Gloss } from '../storage/types'

const dataRoot = path.join(process.cwd(), 'data')
const situationsRoot = path.join(process.cwd(), 'situations')
const storage = new GlossStorage(dataRoot, situationsRoot)

export function setupSituationHandlers() {
  ipcMain.handle('situation:list', async (_, query?: string) => {
    const results: Gloss[] = []
    const lowerQuery = query?.toLowerCase() || null

    for (const gloss of storage.findGlossesByTag('eng:situation')) {
      if (lowerQuery && !gloss.content.toLowerCase().includes(lowerQuery)) {
        continue
      }
      results.push(gloss)
      if (results.length >= 100) break
    }

    return results
  })

  ipcMain.handle('situation:create', async (_, content: string) => {
    const gloss = storage.ensureGloss('eng', content)

    // Add situation tag if not already present
    if (!gloss.tags.includes('eng:situation')) {
      gloss.tags = [...gloss.tags, 'eng:situation']
      storage.saveGloss(gloss)
    }

    return gloss
  })

  ipcMain.handle('situation:export', async () => {
    // TODO: Implement export logic from src/tui/flows/flow_export_situations_batch.py
    // This will be implemented in Phase 6
    return {
      success: false,
      message: 'Export functionality not yet implemented'
    }
  })
}

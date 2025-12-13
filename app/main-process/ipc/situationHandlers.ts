import { ipcMain } from 'electron'
import path from 'path'
import { GlossStorage } from '../storage/fsGlossStorage'

const dataRoot = path.join(process.cwd(), 'data')
const situationsRoot = path.join(process.cwd(), 'situations')
const storage = new GlossStorage(dataRoot, situationsRoot)

export function setupSituationHandlers() {
  ipcMain.handle('situation:list', async (_, query?: string) => {
    const allGlosses = storage.listGlosses('eng')
    const situations = allGlosses.filter((gloss) => gloss.tags?.includes('eng:situation'))

    if (!query) {
      return situations.slice(0, 100) // Limit results
    }

    const lowerQuery = query.toLowerCase()
    return situations
      .filter((s) => s.content.toLowerCase().includes(lowerQuery))
      .slice(0, 100)
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

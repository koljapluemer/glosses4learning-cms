import { ipcMain } from 'electron'
import fs from 'fs'
import path from 'path'

const dataRoot = path.join(process.cwd(), 'data')

export function setupLanguageHandlers() {
  ipcMain.handle('language:list', async () => {
    const languageDir = path.join(dataRoot, 'language')

    if (!fs.existsSync(languageDir)) {
      return []
    }

    const files = fs.readdirSync(languageDir)
    const languages = []

    for (const file of files) {
      if (!file.endsWith('.json')) continue

      try {
        const filePath = path.join(languageDir, file)
        const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'))
        languages.push(data)
      } catch (error) {
        console.error(`Failed to load language file ${file}:`, error)
      }
    }

    return languages
  })
}

import { app, ipcMain } from 'electron'
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'

type AiLogEntry = {
  action: string
  ts?: string
  refs?: string[]
  payload?: Record<string, unknown>
}

function getLogDir(): string {
  return path.join(app.getPath('userData'), 'logs', 'ai')
}

function getLogFile(): string {
  const ts = new Date().toISOString().replace(/[:.]/g, '-')
  const rand = crypto.randomUUID()
  return path.join(getLogDir(), `ai-${ts}-${rand}.log`)
}

async function appendLog(entry: AiLogEntry) {
  const record = {
    ts: new Date().toISOString(),
    ...entry
  }
  const line = `${JSON.stringify(record)}\n`
  const file = getLogFile()
  await fs.promises.mkdir(path.dirname(file), { recursive: true })
  await fs.promises.appendFile(file, line, 'utf8')
}

export function setupAiLogHandlers() {
  ipcMain.handle('ai-log:write', async (_event, entry: AiLogEntry) => {
    try {
      await appendLog(entry)
      return { success: true }
    } catch (err) {
      console.error('Failed to write AI log', err)
      return { success: false, error: (err as Error).message }
    }
  })
}

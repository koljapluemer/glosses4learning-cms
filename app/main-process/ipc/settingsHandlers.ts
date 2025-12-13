import { ipcMain } from 'electron'
import Store from 'electron-store'

const store = new Store()

export function setupSettingsHandlers() {
  ipcMain.handle('settings:get', async (_, key: string) => {
    return store.get(key)
  })

  ipcMain.handle('settings:set', async (_, key: string, value: unknown) => {
    store.set(key, value)
  })
}

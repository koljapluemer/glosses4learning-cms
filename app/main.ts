import { app, BrowserWindow } from 'electron'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { setupGlossHandlers } from './main-process/ipc/glossHandlers'
import { setupLanguageHandlers } from './main-process/ipc/languageHandlers'
import { setupSituationHandlers } from './main-process/ipc/situationHandlers'
import { setupSettingsHandlers } from './main-process/ipc/settingsHandlers'
import { setupAiLogHandlers } from './main-process/ipc/aiLogHandlers'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// The built directory structure
//
// ├─┬─┬ dist-electron
// │ │ └── main.js
// │ ├─┬ dist-renderer
// │ │ └── index.html

process.env.APP_ROOT = path.join(__dirname, '..')

// Disable sandbox for development (Linux fix)
if (process.platform === 'linux') {
  app.commandLine.appendSwitch('no-sandbox')
}

let win: BrowserWindow | null

function createWindow() {
  win = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  // Test active push message to Renderer-process
  win.webContents.on('did-finish-load', () => {
    win?.webContents.send('main-process-message', new Date().toLocaleString())
  })

  // Standard electron-vite pattern: use ELECTRON_RENDERER_URL in dev, file in prod
  if (!app.isPackaged && process.env['ELECTRON_RENDERER_URL']) {
    win.loadURL(process.env['ELECTRON_RENDERER_URL'])
    win.webContents.openDevTools()
  } else {
    win.loadFile(path.join(__dirname, '../renderer/index.html'))
  }
}

// Quit when all windows are closed
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
    win = null
  }
})

app.on('activate', () => {
  // On OS X it's common to re-create a window in the app when the
  // dock icon is clicked and there are no other windows open.
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow()
  }
})

app.whenReady().then(() => {
  // Setup IPC handlers
  setupGlossHandlers()
  setupLanguageHandlers()
  setupSituationHandlers()
  setupSettingsHandlers()
  setupAiLogHandlers()

  createWindow()
})

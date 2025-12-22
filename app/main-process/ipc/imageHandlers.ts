import { ipcMain, dialog } from 'electron'
import path from 'path'
import fs from 'fs/promises'
import fsSync from 'fs'
import sharp from 'sharp'

const dataRoot = path.join(process.cwd(), 'data')
const imageDir = path.join(dataRoot, 'images')

// Ensure directory exists
if (!fsSync.existsSync(imageDir)) {
  fsSync.mkdirSync(imageDir, { recursive: true })
}

function sanitizeFilename(input: string): string {
  // Only allow alphanumeric and underscores
  return input.replace(/[^a-zA-Z0-9_]/g, '_').toLowerCase()
}

export function setupImageHandlers() {
  // Upload image: resize, convert to webp, save
  ipcMain.handle('image:upload', async (_, base64Data: string, userSlug: string) => {
    const slug = sanitizeFilename(userSlug)
    if (!slug) throw new Error('Invalid filename')

    const filename = `${slug}.webp`
    const filepath = path.join(imageDir, filename)

    // Check if file already exists (enforce unique filenames)
    if (fsSync.existsSync(filepath)) {
      throw new Error(`Filename already exists: ${filename}`)
    }

    // Decode base64
    const buffer = Buffer.from(base64Data, 'base64')

    // Process: resize to 600px wide, keep aspect ratio, convert to webp
    await sharp(buffer)
      .resize(600, null, { withoutEnlargement: true })
      .webp({ quality: 85 })
      .toFile(filepath)

    return filename
  })

  // Check if filename exists (for validation)
  ipcMain.handle('image:exists', async (_, filename: string) => {
    const filepath = path.join(imageDir, filename)
    return fsSync.existsSync(filepath)
  })

  // Delete image file
  ipcMain.handle('image:delete', async (_, filename: string) => {
    const filepath = path.join(imageDir, filename)
    if (fsSync.existsSync(filepath)) {
      await fs.unlink(filepath)
    }
  })

  // Get image as base64 (for preview)
  ipcMain.handle('image:load', async (_, filename: string) => {
    const filepath = path.join(imageDir, filename)
    const buffer = await fs.readFile(filepath)
    return buffer.toString('base64')
  })

  // Open file picker
  ipcMain.handle('image:pickFile', async () => {
    const result = await dialog.showOpenDialog({
      properties: ['openFile'],
      filters: [
        { name: 'Images', extensions: ['jpg', 'jpeg', 'png', 'gif', 'webp'] }
      ]
    })

    if (result.canceled || !result.filePaths[0]) return null

    const buffer = await fs.readFile(result.filePaths[0])
    return buffer.toString('base64')
  })
}

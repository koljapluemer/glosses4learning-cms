import { ipcMain, dialog } from 'electron'
import path from 'path'
import fs from 'fs/promises'
import fsSync from 'fs'
import ffmpeg from 'fluent-ffmpeg'
import ffmpegStatic from 'ffmpeg-static'
import { tmpdir } from 'os'

const dataRoot = path.join(process.cwd(), 'data')
const audioDir = path.join(dataRoot, 'audio')

// Ensure directory exists
if (!fsSync.existsSync(audioDir)) {
  fsSync.mkdirSync(audioDir, { recursive: true })
}

// Configure ffmpeg to use static binary
if (ffmpegStatic) {
  ffmpeg.setFfmpegPath(ffmpegStatic)
}

export function setupAudioHandlers() {
  // Upload audio: convert to MP3 with volume normalization, save
  ipcMain.handle('audio:upload', async (_, base64Data: string, glossSlug: string, index: number) => {
    const filename = `${glossSlug}_${index}.mp3`
    const filepath = path.join(audioDir, filename)

    // Check if file already exists (enforce unique filenames)
    if (fsSync.existsSync(filepath)) {
      throw new Error(`Filename already exists: ${filename}`)
    }

    // Decode base64
    const buffer = Buffer.from(base64Data, 'base64')

    // Create temporary input file
    const tempInputPath = path.join(tmpdir(), `audio_input_${Date.now()}`)
    await fs.writeFile(tempInputPath, buffer)

    try {
      // Process audio: convert to MP3 with volume normalization
      await new Promise<void>((resolve, reject) => {
        ffmpeg(tempInputPath)
          .audioCodec('libmp3lame')
          .audioBitrate(128)
          .audioFilters('loudnorm=I=-16:TP=-1.5:LRA=11') // EBU R128 normalization
          .toFormat('mp3')
          .on('end', () => resolve())
          .on('error', (err) => reject(err))
          .save(filepath)
      })

      return filename
    } finally {
      // Clean up temporary file
      try {
        await fs.unlink(tempInputPath)
      } catch (error) {
        // Ignore cleanup errors
      }
    }
  })

  // Check if filename exists (for validation)
  ipcMain.handle('audio:exists', async (_, filename: string) => {
    const filepath = path.join(audioDir, filename)
    return fsSync.existsSync(filepath)
  })

  // Delete audio file
  ipcMain.handle('audio:delete', async (_, filename: string) => {
    const filepath = path.join(audioDir, filename)
    if (fsSync.existsSync(filepath)) {
      await fs.unlink(filepath)
    }
  })

  // Get audio as base64 (for playback)
  ipcMain.handle('audio:load', async (_, filename: string) => {
    const filepath = path.join(audioDir, filename)
    const buffer = await fs.readFile(filepath)
    return buffer.toString('base64')
  })

  // Open file picker
  ipcMain.handle('audio:pickFile', async () => {
    const result = await dialog.showOpenDialog({
      properties: ['openFile'],
      filters: [
        { name: 'Audio Files', extensions: ['mp3', 'wav', 'ogg', 'm4a', 'aac', 'flac', 'wma'] }
      ]
    })

    if (result.canceled || !result.filePaths[0]) return null

    const buffer = await fs.readFile(result.filePaths[0])
    return buffer.toString('base64')
  })
}

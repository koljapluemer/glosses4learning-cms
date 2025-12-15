import { ipcMain } from 'electron'
import path from 'path'
import fs from 'fs'
import { GlossStorage } from '../storage/fsGlossStorage'
import type { Gloss } from '../storage/types'
import { buildGoalNodes, type TreeNode } from '../../renderer/entities/glosses/treeBuilder'

const dataRoot = path.join(process.cwd(), 'data')
const situationsRoot = path.join(process.cwd(), 'situations')
const storage = new GlossStorage(dataRoot, situationsRoot)

export type SituationExportResult = {
  success: boolean
  error?: string
  totalSituations: number
  totalExports: number
  exports: Array<{
    situation: string
    native: string
    target: string
    situation_json: string
    glosses_jsonl: string
    stats: { goal_count: number; gloss_count: number; excluded_count: number }
  }>
  skipped: Array<{
    situation: string
    native: string
    target: string
    reason: string
  }>
  outputRoot: string
}

function loadLanguageCodes(): string[] {
  const langDir = path.join(dataRoot, 'language')
  if (!fs.existsSync(langDir)) return []
  return fs
    .readdirSync(langDir)
    .filter((f) => f.endsWith('.json'))
    .map((file) => {
      try {
        const data = JSON.parse(fs.readFileSync(path.join(langDir, file), 'utf-8'))
        return (data.isoCode || data.iso_code || file.replace('.json', '')).trim().toLowerCase()
      } catch (err) {
        console.warn('Failed to read language file', file, err)
        return ''
      }
    })
    .filter(Boolean)
}

function nodeRef(gl: Gloss): string {
  return `${gl.language}:${gl.slug || gl.content}`
}

function gatherRefs(root: TreeNode): { refs: string[]; learn: string[] } {
  const refs: string[] = []
  const learn: string[] = []
  const seen = new Set<string>()

  function walk(node: TreeNode) {
    const ref = nodeRef(node.gloss)
    if (!seen.has(ref)) {
      seen.add(ref)
      refs.push(ref)
    }
    if (node.bold && ref !== nodeRef(root.gloss) && !learn.includes(ref)) {
      learn.push(ref)
    }
    for (const child of node.children || []) {
      walk(child)
    }
  }

  walk(root)
  return { refs, learn }
}

function cleanupOldExports(outputRoot: string, expectedFiles: Set<string>) {
  if (!fs.existsSync(outputRoot)) return

  for (const native of fs.readdirSync(outputRoot)) {
    const nativeDir = path.join(outputRoot, native)
    if (!fs.statSync(nativeDir).isDirectory()) continue

    for (const target of fs.readdirSync(nativeDir)) {
      const targetDir = path.join(nativeDir, target)
      if (!fs.statSync(targetDir).isDirectory()) continue

      for (const file of fs.readdirSync(targetDir)) {
        const filePath = path.join(targetDir, file)
        const stat = fs.statSync(filePath)
        if (stat.isDirectory()) continue

        const lower = file.toLowerCase()
        const isExportFile = lower.endsWith('.json') || lower.endsWith('.jsonl') || lower.endsWith('.webp')
        if (!isExportFile) continue

        if (!expectedFiles.has(filePath)) {
          fs.unlinkSync(filePath)
        }
      }

      if (fs.existsSync(targetDir) && fs.readdirSync(targetDir).length === 0) {
        fs.rmdirSync(targetDir)
      }
    }

    if (fs.existsSync(nativeDir) && fs.statSync(nativeDir).isDirectory() && fs.readdirSync(nativeDir).length === 0) {
      fs.rmdirSync(nativeDir)
    }
  }
}

function performBatchExport(): SituationExportResult {
  const outputRoot = situationsRoot
  const result: SituationExportResult = {
    success: false,
    error: undefined as string | undefined,
    totalSituations: 0,
    totalExports: 0,
    exports: [],
    skipped: [],
    outputRoot
  }

  try {
    const exportedFiles = new Set<string>()
    const nativeLanguagesUsed = new Set<string>()
    const targetLanguagesByNative = new Map<string, Set<string>>()
    const situationsByNativeTarget = new Map<string, Map<string, { [situation: string]: boolean }>>()
    const situations: Gloss[] = []
    for (const gloss of storage.findGlossesByTag('eng:situation')) {
      situations.push(gloss)
    }
    result.totalSituations = situations.length

    const languages = loadLanguageCodes()
    if (languages.length < 2) {
      result.error = 'Need at least 2 configured languages'
      return result
    }

    for (const situation of situations) {
      for (const native of languages) {
        for (const target of languages) {
          if (native === target) continue

          const { nodes } = buildGoalNodes(situation, storage, native, target)
          if (!nodes.length) {
            result.skipped.push({
              situation: `${situation.language}:${situation.slug}`,
              native,
              target,
              reason: 'No learnable content'
            })
            continue
          }

          const exportObj: {
            'procedural-paraphrase-expression-goals': string[]
            'understand-expression-goals': string[]
          } = {
            'procedural-paraphrase-expression-goals': [],
            'understand-expression-goals': []
          }
          const allRefs = new Set<string>()
          const situationRef = `${situation.language}:${situation.slug}`
          allRefs.add(situationRef)
          for (const ref of situation.translations || []) {
            if (ref.startsWith(`${native}:`) || ref.startsWith(`${target}:`)) {
              allRefs.add(ref)
            }
          }

          for (const root of nodes) {
            const state = (root.state || '').toLowerCase()
            if (state !== 'yellow') continue
            const goalType = root.goal_type
            if (goalType !== 'procedural' && goalType !== 'understanding') continue

            const { refs } = gatherRefs(root)
            refs.forEach((r) => allRefs.add(r))
            const challenge = nodeRef(root.gloss)
            if (goalType === 'procedural') {
              exportObj['procedural-paraphrase-expression-goals'].push(challenge)
            } else {
              exportObj['understand-expression-goals'].push(challenge)
            }
          }

          if (
            !exportObj['procedural-paraphrase-expression-goals'].length &&
            !exportObj['understand-expression-goals'].length
          ) {
            result.skipped.push({
              situation: `${situation.language}:${situation.slug}`,
              native,
              target,
              reason: 'No learnable content'
            })
            continue
          }

          const jsonlLines: string[] = []
          let excludedCount = 0
          for (const ref of Array.from(allRefs).sort()) {
            const gloss = storage.resolveReference(ref)
            if (!gloss) continue
            if (gloss.needsHumanCheck || gloss.excludeFromLearning) {
              excludedCount += 1
              continue
            }
            const { slug, ...rest } = gloss as Gloss
            void slug
            jsonlLines.push(JSON.stringify({ ...rest, ref }, null, 0))
          }

          const outputDir = path.join(outputRoot, native, target)
          fs.mkdirSync(outputDir, { recursive: true })
          const baseFilename = situation.content
          const situationJsonPath = path.join(outputDir, `${baseFilename}.json`)
          const glossesJsonlPath = path.join(outputDir, `${baseFilename}.jsonl`)

          let situationImageFilename: string | false = false

          // Handle decorative image export (only for situation glosses)
          if (situation.decorativeImages && situation.decorativeImages.length > 0) {
            const randomIndex = Math.floor(Math.random() * situation.decorativeImages.length)
            const selectedImage = situation.decorativeImages[randomIndex]

            const sourceImagePath = path.join(dataRoot, 'images', selectedImage)
            if (fs.existsSync(sourceImagePath)) {
              situationImageFilename = `${baseFilename}.webp`
              const situationImagePath = path.join(outputDir, situationImageFilename)

              fs.copyFileSync(sourceImagePath, situationImagePath)
              exportedFiles.add(situationImagePath)
            }
          }

          // Write situation JSON without image field
          fs.writeFileSync(situationJsonPath, JSON.stringify(exportObj, null, 2), 'utf-8')
          fs.writeFileSync(glossesJsonlPath, jsonlLines.join('\n'), 'utf-8')
          exportedFiles.add(situationJsonPath)
          exportedFiles.add(glossesJsonlPath)

          // Track metadata
          nativeLanguagesUsed.add(native)
          if (!targetLanguagesByNative.has(native)) {
            targetLanguagesByNative.set(native, new Set())
          }
          targetLanguagesByNative.get(native)!.add(target)

          if (!situationsByNativeTarget.has(native)) {
            situationsByNativeTarget.set(native, new Map())
          }
          if (!situationsByNativeTarget.get(native)!.has(target)) {
            situationsByNativeTarget.get(native)!.set(target, {})
          }
          situationsByNativeTarget.get(native)!.get(target)![baseFilename] = situationImageFilename !== false

          result.exports.push({
            situation: situationRef,
            native,
            target,
            situation_json: situationJsonPath,
            glosses_jsonl: glossesJsonlPath,
            stats: {
              goal_count: nodes.length,
              gloss_count: allRefs.size,
              excluded_count: excludedCount
            }
          })
          result.totalExports += 1
        }
      }
    }

    // Write metadata files
    // 1. Root level: available_native_languages.json
    const nativeLanguagesArray = Array.from(nativeLanguagesUsed).sort()
    const nativeLanguagesJsonPath = path.join(outputRoot, 'available_native_languages.json')
    fs.writeFileSync(nativeLanguagesJsonPath, JSON.stringify(nativeLanguagesArray, null, 2), 'utf-8')
    exportedFiles.add(nativeLanguagesJsonPath)

    // 2. For each native language: available_target_languages.json
    for (const native of nativeLanguagesUsed) {
      const targets = Array.from(targetLanguagesByNative.get(native)!).sort()
      const targetsJsonPath = path.join(outputRoot, native, 'available_target_languages.json')
      fs.writeFileSync(targetsJsonPath, JSON.stringify(targets, null, 2), 'utf-8')
      exportedFiles.add(targetsJsonPath)
    }

    // 3. For each native/target combination: situations.json
    for (const [native, targetsMap] of situationsByNativeTarget) {
      for (const [target, situationsMap] of targetsMap) {
        const situationsJsonPath = path.join(outputRoot, native, target, 'situations.json')
        fs.writeFileSync(situationsJsonPath, JSON.stringify(situationsMap, null, 2), 'utf-8')
        exportedFiles.add(situationsJsonPath)
      }
    }

    cleanupOldExports(outputRoot, exportedFiles)
    result.success = true
    return result
  } catch (err) {
    console.error('Batch export failed', err)
    result.error = err instanceof Error ? err.message : String(err)
    result.success = false
    return result
  }
}

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

    if (!gloss.tags.includes('eng:situation')) {
      gloss.tags = [...gloss.tags, 'eng:situation']
      storage.saveGloss(gloss)
    }

    return gloss
  })

  ipcMain.handle('situation:export', async () => {
    return performBatchExport()
  })
}

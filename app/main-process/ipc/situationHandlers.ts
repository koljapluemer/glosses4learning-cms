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
  const skipParts = root.goal_type === 'procedural'

  function walk(node: TreeNode) {
    if (skipParts && (node.role === 'part' || node.role === 'usage_part')) return
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

          type GoalPayload = { finalChallenge: string; needToBeLearned: string[]; references: string[] }
          const exportObj: {
            'procedural-paraphrase-expression-goals': GoalPayload[]
            'understand-expression-goals': GoalPayload[]
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
            if (state !== 'yellow' && state !== 'green') continue
            const goalType = root.goal_type
            if (goalType !== 'procedural' && goalType !== 'understand') continue

            const { refs, learn } = gatherRefs(root)
            refs.forEach((r) => allRefs.add(r))
            const payload = {
              finalChallenge: nodeRef(root.gloss),
              needToBeLearned: learn,
              references: refs
            }
            if (goalType === 'procedural') {
              exportObj['procedural-paraphrase-expression-goals'].push(payload)
            } else {
              exportObj['understand-expression-goals'].push(payload)
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

          fs.writeFileSync(situationJsonPath, JSON.stringify(exportObj, null, 2), 'utf-8')
          fs.writeFileSync(glossesJsonlPath, jsonlLines.join('\n'), 'utf-8')

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

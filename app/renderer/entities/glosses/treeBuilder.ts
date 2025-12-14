/**
 * Tree building for goal nodes with statistics and warnings
 * Port of src/shared/tree.py:234-428
 */

import type { Gloss } from '../../../main-process/storage/types'
import type { GlossStorage } from '../../../main-process/storage/fsGlossStorage'
import {
  detectGoalType,
  determineGoalState,
  paraphraseDisplay,
  SPLIT_LOG_MARKER,
  TRANSLATION_IMPOSSIBLE_MARKER,
  USAGE_IMPOSSIBLE_MARKER
} from './goalState'
import type { RelationshipField } from './relationRules'

function normalizeLanguageCode(code: string | null | undefined): string {
  return (code || '').trim().toLowerCase()
}

export interface TreeNode {
  gloss: Gloss
  display: string
  children: TreeNode[]
  marker: string
  bold: boolean
  role: string
  warn_native_missing: boolean
  warn_target_missing: boolean
  warn_usage_missing: boolean
  warn_parts_missing: boolean
  state: 'red' | 'yellow' | 'green' | ''
  goal_type?: 'procedural' | 'understand'
  parentRef?: string
  viaField?: RelationshipField
}

export interface TreeStats {
  situation_glosses: Set<string>
  glosses_to_learn: Set<string>
  native_missing: Set<string>
  target_missing: Set<string>
  parts_missing: Set<string>
  usage_missing: Set<string>
  gloss_map: Record<string, Gloss>
}

/**
 * Build goal nodes for a situation with statistics and warnings
 * Python ref: src/shared/tree.py:234-427
 */
export function buildGoalNodes(
  situation: Gloss,
  storage: GlossStorage,
  nativeLanguage: string,
  targetLanguage: string
): { nodes: TreeNode[]; stats: TreeStats } {
  const native = normalizeLanguageCode(nativeLanguage)
  const target = normalizeLanguageCode(targetLanguage)

  const stats: TreeStats = {
    situation_glosses: new Set(),
    glosses_to_learn: new Set(),
    native_missing: new Set(),
    target_missing: new Set(),
    parts_missing: new Set(),
    usage_missing: new Set(),
    gloss_map: {}
  }

  const seenKeys = new Set<string>()
  const nodes: TreeNode[] = []

  function glossKey(gl: Gloss): string {
    return `${gl.language}:${gl.slug || gl.content}`
  }

  function hasLog(gl: Gloss, marker: string): boolean {
    const logs = gl.logs || {}
    if (typeof logs !== 'object') return false
    return Object.values(logs).some((val) => String(val).includes(marker))
  }

  function hasTranslation(gl: Gloss, lang: string): boolean {
    return (gl.translations || []).some((ref) => ref.startsWith(`${lang}:`))
  }

  function markStats(
    gl: Gloss,
    usageLineage: boolean,
    partsLine: boolean,
    learnLang: string
  ): {
    warn_native_missing: boolean
    warn_target_missing: boolean
    warn_usage_missing: boolean
  } {
    const key = glossKey(gl)
    stats.gloss_map[key] = gl
    stats.situation_glosses.add(key)

    // Skip parts-missing warning for procedural paraphrase goals (we don't split them)
    let skipPartsWarning = false
    if (
      gl.language === native &&
      (gl.tags || []).includes('eng:procedural-paraphrase-expression-goal')
    ) {
      skipPartsWarning = true
    }

    if (
      !skipPartsWarning &&
      !(gl.parts || []).length &&
      !hasLog(gl, SPLIT_LOG_MARKER)
    ) {
      stats.parts_missing.add(key)
    }

    if (gl.language === target) {
      if (!hasTranslation(gl, native) && !hasLog(gl, `${TRANSLATION_IMPOSSIBLE_MARKER}:${native}`)) {
        stats.native_missing.add(key)
      }
      if (
        !usageLineage &&
        !hasLog(gl, `${USAGE_IMPOSSIBLE_MARKER}:${target}`) &&
        !(gl.usage_examples || []).length
      ) {
        stats.usage_missing.add(key)
      }
    } else if (gl.language === native) {
      if (!hasTranslation(gl, target) && !hasLog(gl, `${TRANSLATION_IMPOSSIBLE_MARKER}:${target}`)) {
        stats.target_missing.add(key)
      }
    }

    if (partsLine && gl.language === learnLang) {
      stats.glosses_to_learn.add(key)
    }

    return {
      warn_native_missing: stats.native_missing.has(key),
      warn_target_missing: stats.target_missing.has(key),
      warn_usage_missing: stats.usage_missing.has(key)
    }
  }

  function buildNode(
    gloss: Gloss,
    role: string = 'root',
    marker: string = '',
    usageLineage: boolean = false,
    allowTranslations: boolean = true,
    path: Set<string> | null = null,
    partsLine: boolean = false,
    learnLang: string = '',
    parentRef: string | null = null,
    viaField: RelationshipField | null = null
  ): TreeNode | null {
    const tags = gloss.tags || []
    if (gloss.language === target && tags.includes('eng:paraphrase')) {
      return null
    }

    const currentPath = new Set(path || [])
    const key = glossKey(gloss)
    seenKeys.add(key)

    const flags = markStats(gloss, usageLineage, partsLine, learnLang)

    const node: TreeNode = {
      gloss,
      display: paraphraseDisplay(gloss),
      children: [],
      marker,
      bold: partsLine && gloss.language === learnLang,
      role,
      warn_native_missing: flags.warn_native_missing,
      warn_target_missing: flags.warn_target_missing,
      warn_usage_missing: flags.warn_usage_missing,
      warn_parts_missing: stats.parts_missing.has(key),
      state: role === 'root' ? determineGoalState(gloss, storage, native, target) : '',
      parentRef: parentRef || undefined,
      viaField: viaField || undefined
    }

    if (currentPath.has(key)) {
      return node
    }
    const nextPath = new Set(currentPath)
    nextPath.add(key)

    if (['root', 'part', 'usage_part'].includes(role)) {
      stats.glosses_to_learn.add(key)
    }

    const isProceduralRoot =
      role === 'root' &&
      gloss.language === native &&
      (gloss.tags || []).includes('eng:procedural-paraphrase-expression-goal')

    // Parts expansion (skip for procedural root goals)
    for (const partRef of isProceduralRoot ? [] : gloss.parts || []) {
      const partGloss = storage.resolveReference(partRef)
      if (!partGloss) continue

      const childPartsLine = role === 'root' ? partsLine : false
      const partNode = buildNode(
        partGloss,
        ['usage', 'usage_part'].includes(role) ? 'usage_part' : 'part',
        '',
        usageLineage,
        true,
        nextPath,
        childPartsLine,
        learnLang,
        `${gloss.language}:${gloss.slug || gloss.content}`,
        'parts'
      )
      if (partNode) {
        node.children.push(partNode)
      }
    }

    // Translation expansion
    if (allowTranslations) {
      let otherLang: string | null = null
      if (gloss.language === native && target) {
        otherLang = target
      } else if (gloss.language === target && native) {
        otherLang = native
      }
      if (otherLang) {
        for (const ref of gloss.translations || []) {
          const refLang = ref.split(':')[0]?.trim().toLowerCase()
          if (refLang !== otherLang.toLowerCase()) continue

          const tGloss = storage.resolveReference(ref)
          if (!tGloss) continue

          const childKey = glossKey(tGloss)
          const tNode = buildNode(
            tGloss,
            'translation',
            '',
            usageLineage,
            !nextPath.has(childKey),
            nextPath,
            false,
            learnLang,
            `${gloss.language}:${gloss.slug || gloss.content}`,
            'translations'
          )
          if (tNode) {
            node.children.push(tNode)
          }
        }
      }
    }

    // Usage examples expansion (only for target language, not in usage lineage)
    if (gloss.language === target && !usageLineage) {
      if (gloss.usage_examples) {
        for (const uRef of gloss.usage_examples) {
          const uGloss = storage.resolveReference(uRef)
          if (!uGloss) continue

          const usageNode = buildNode(
            uGloss,
            'usage',
            'USG ',
            true,
            true,
            nextPath,
            false,
            learnLang,
            `${gloss.language}:${gloss.slug || gloss.content}`,
            'usage_examples'
          )
          if (usageNode) {
            node.children.push(usageNode)
          }
        }
      }
    }

    return node
  }

  // Build nodes for each goal child of the situation
  for (const ref of situation.children || []) {
    const gloss = storage.resolveReference(ref)
    if (!gloss) continue

    const goalKind = detectGoalType(gloss, native, target)
    let marker = ''
    let learnLang = ''
    let goalType: 'procedural' | 'understand' | undefined

    if (goalKind === 'procedural') {
      marker = 'PROC '
      learnLang = native
      goalType = 'procedural'
    } else if (goalKind === 'understanding') {
      marker = 'UNDR '
      learnLang = target
      goalType = 'understand'
    } else {
      continue
    }

    const node = buildNode(
      gloss,
      'root',
      marker,
      false,
      true,
      null,
      true,
      learnLang,
      `${situation.language}:${situation.slug || situation.content}`,
      'children'
    )
    if (node) {
      node.goal_type = goalType
      nodes.push(node)
    }
  }

  return { nodes, stats }
}

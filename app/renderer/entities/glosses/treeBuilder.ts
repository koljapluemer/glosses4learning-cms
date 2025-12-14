/**
 * Tree building for goal nodes with statistics and warnings
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
  state: 'red' | 'yellow' | ''
  goal_type?: 'procedural' | 'understanding'
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
  goal_missing_by_root: Record<
    string,
    {
      native_missing: Set<string>
      target_missing: Set<string>
      parts_missing: Set<string>
      usage_missing: Set<string>
    }
  >
}

function glossKey(gl: Gloss): string {
  return `${gl.language}:${gl.slug || gl.content}`
}

function hasLog(gl: Gloss, marker: string): boolean {
  const logs = gl.logs || {}
  if (typeof logs !== 'object') return false
  return Object.values(logs).some((val) => String(val).includes(marker))
}

function translationExists(
  storage: GlossStorage,
  gl: Gloss,
  lang: string,
  requireNonParaphrase: boolean = false
): boolean {
  return (gl.translations || []).some((ref) => {
    const [refLang] = ref.split(':')
    if (normalizeLanguageCode(refLang) !== lang) return false
    if (!requireNonParaphrase) return true
    const tGloss = storage.resolveReference(ref)
    if (!tGloss) return false
    return !(tGloss.tags || []).includes('eng:paraphrase')
  })
}

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
    gloss_map: {},
    goal_missing_by_root: {}
  }

  function ensureGoalStats(goalRef: string) {
    if (!stats.goal_missing_by_root[goalRef]) {
      stats.goal_missing_by_root[goalRef] = {
        native_missing: new Set(),
        target_missing: new Set(),
        parts_missing: new Set(),
        usage_missing: new Set()
      }
    }
    return stats.goal_missing_by_root[goalRef]
  }

  type MissingField = 'native_missing' | 'target_missing' | 'parts_missing' | 'usage_missing'

  function recordMissing(kind: 'native' | 'target' | 'parts' | 'usage', key: string, goalRef: string) {
    const map: Record<typeof kind, MissingField> = {
      native: 'native_missing',
      target: 'target_missing',
      parts: 'parts_missing',
      usage: 'usage_missing'
    }
    const field = map[kind]
    stats[field].add(key)
    ensureGoalStats(goalRef)[field].add(key)
  }

  function computeWarnings(
    gl: Gloss,
    goalRootRef: string,
    options: {
      checkTranslationTo?: string
      requireNonParaphrase?: boolean
      checkParts?: boolean
      checkUsage?: boolean
    }
  ): {
    warn_native_missing: boolean
    warn_target_missing: boolean
    warn_usage_missing: boolean
    warn_parts_missing: boolean
  } {
    const key = glossKey(gl)
    stats.gloss_map[key] = gl
    stats.situation_glosses.add(key)

    if (options.checkParts && !(gl.parts || []).length && !hasLog(gl, SPLIT_LOG_MARKER)) {
      recordMissing('parts', key, goalRootRef)
    }

    if (options.checkTranslationTo) {
      const desiredLang = normalizeLanguageCode(options.checkTranslationTo)
      const missingTranslation =
        !translationExists(storage, gl, desiredLang, options.requireNonParaphrase) &&
        !hasLog(gl, `${TRANSLATION_IMPOSSIBLE_MARKER}:${desiredLang}`)

      if (missingTranslation) {
        if (desiredLang === native) {
          recordMissing('native', key, goalRootRef)
        } else if (desiredLang === target) {
          recordMissing('target', key, goalRootRef)
        }
      }
    }

    if (
      options.checkUsage &&
      normalizeLanguageCode(gl.language) === target &&
      !(gl.usage_examples || []).length &&
      !hasLog(gl, `${USAGE_IMPOSSIBLE_MARKER}:${target}`)
    ) {
      recordMissing('usage', key, goalRootRef)
    }

    return {
      warn_native_missing: stats.native_missing.has(key),
      warn_target_missing: stats.target_missing.has(key),
      warn_usage_missing: stats.usage_missing.has(key),
      warn_parts_missing: stats.parts_missing.has(key)
    }
  }

  function addLearnable(gl: Gloss, learnLang: string, partsLine: boolean) {
    if (partsLine && normalizeLanguageCode(gl.language) === normalizeLanguageCode(learnLang)) {
      stats.glosses_to_learn.add(glossKey(gl))
    }
  }

  function buildTranslationNodes(
    gl: Gloss,
    otherLang: string,
    path: Set<string>,
    goalRootRef: string,
    parentRef: string,
    viaField: RelationshipField,
    requireNonParaphrase: boolean = false
  ): TreeNode[] {
    const nodes: TreeNode[] = []
    for (const ref of gl.translations || []) {
      const [refLang] = ref.split(':')
      if (normalizeLanguageCode(refLang) !== otherLang) continue
      const tGloss = storage.resolveReference(ref)
      if (!tGloss) continue
      if (requireNonParaphrase && (tGloss.tags || []).includes('eng:paraphrase')) continue

      const warnings = computeWarnings(tGloss, goalRootRef, {})
      const node: TreeNode = {
        gloss: tGloss,
        display: paraphraseDisplay(tGloss),
        children: [],
        marker: '',
        bold: false,
        role: 'translation',
        warn_native_missing: warnings.warn_native_missing,
        warn_target_missing: warnings.warn_target_missing,
        warn_usage_missing: warnings.warn_usage_missing,
        warn_parts_missing: warnings.warn_parts_missing,
        state: '',
        parentRef,
        viaField
      }

      // Path-based cycle cut
      if (!path.has(glossKey(tGloss))) {
        // leave as leaf regardless
      }
      nodes.push(node)
    }
    return nodes
  }

  function buildUsageNode(
    uGloss: Gloss,
    path: Set<string>,
    goalRootRef: string,
    parentRef: string,
    viaField: RelationshipField
  ): TreeNode {
    const counterpart =
      normalizeLanguageCode(uGloss.language) === target ? native : normalizeLanguageCode(uGloss.language) === native ? target : null
    const warnings = computeWarnings(uGloss, goalRootRef, {
      checkTranslationTo: counterpart || undefined,
      requireNonParaphrase: normalizeLanguageCode(uGloss.language) === native
    })

    const node: TreeNode = {
      gloss: uGloss,
      display: paraphraseDisplay(uGloss),
      children: [],
      marker: 'USG ',
      bold: false,
      role: 'usage',
      warn_native_missing: warnings.warn_native_missing,
      warn_target_missing: warnings.warn_target_missing,
      warn_usage_missing: warnings.warn_usage_missing,
      warn_parts_missing: warnings.warn_parts_missing,
      state: '',
      parentRef,
      viaField
    }

    if (path.has(glossKey(uGloss))) {
      return node
    }
    const nextPath = new Set(path)
    nextPath.add(glossKey(uGloss))

    if (counterpart) {
      node.children.push(
        ...buildTranslationNodes(
          uGloss,
          counterpart,
          nextPath,
          goalRootRef,
          glossKey(uGloss),
          'translations',
          normalizeLanguageCode(uGloss.language) === native
        )
      )
    }

    return node
  }

  function buildPartsNodes(
    gl: Gloss,
    path: Set<string>,
    goalRootRef: string,
    learnLang: string,
    partsLine: boolean,
    options?: { skipUsageForNode?: boolean }
  ): TreeNode[] {
    const nodes: TreeNode[] = []
    for (const partRef of gl.parts || []) {
      const partGloss = storage.resolveReference(partRef)
      if (!partGloss) continue

      const lang = normalizeLanguageCode(partGloss.language)
      const counterpart = lang === target ? native : lang === native ? target : null
      const warnings = computeWarnings(partGloss, goalRootRef, {
        checkTranslationTo: counterpart || undefined,
        requireNonParaphrase: lang === native,
        checkParts: true,
        checkUsage: !options?.skipUsageForNode && lang === target
      })

      const partKey = glossKey(partGloss)
      const node: TreeNode = {
        gloss: partGloss,
        display: paraphraseDisplay(partGloss),
        children: [],
        marker: '',
        bold: partsLine && lang === normalizeLanguageCode(learnLang),
        role: 'part',
        warn_native_missing: warnings.warn_native_missing,
        warn_target_missing: warnings.warn_target_missing,
        warn_usage_missing: warnings.warn_usage_missing,
        warn_parts_missing: warnings.warn_parts_missing,
        state: '',
        parentRef: glossKey(gl),
        viaField: 'parts'
      }

      addLearnable(partGloss, learnLang, partsLine)

      if (path.has(partKey)) {
        nodes.push(node)
        continue
      }
      const nextPath = new Set(path)
      nextPath.add(partKey)

      if (counterpart) {
        node.children.push(
          ...buildTranslationNodes(
            partGloss,
            counterpart,
            nextPath,
            goalRootRef,
            partKey,
            'translations',
            lang === native
          )
        )
      }

      if (!options?.skipUsageForNode && lang === target) {
        for (const uRef of partGloss.usage_examples || []) {
          const uGloss = storage.resolveReference(uRef)
          if (!uGloss) continue
          node.children.push(buildUsageNode(uGloss, nextPath, goalRootRef, partKey, 'usage_examples'))
        }
      }

      node.children.push(...buildPartsNodes(partGloss, nextPath, goalRootRef, learnLang, partsLine))
      nodes.push(node)
    }
    return nodes
  }

  const nodes: TreeNode[] = []

  for (const ref of situation.children || []) {
    const gloss = storage.resolveReference(ref)
    if (!gloss) continue

    const goalKind = detectGoalType(gloss, native, target)
    let marker = ''
    let learnLang = ''
    let goalType: 'procedural' | 'understanding' | undefined

    if (goalKind === 'procedural') {
      marker = 'PROC '
      learnLang = native
      goalType = 'procedural'
    } else if (goalKind === 'understanding') {
      marker = 'UNDR '
      learnLang = target
      goalType = 'understanding'
    } else {
      continue
    }

    const rootKey = glossKey(gloss)
    const goalRootRef = `${gloss.language}:${gloss.slug || gloss.content}`
    const rootWarnings = computeWarnings(gloss, goalRootRef, {
      checkTranslationTo: goalKind === 'understanding' ? native : target,
      requireNonParaphrase: goalKind === 'procedural',
      checkParts: true,
      checkUsage: false
    })

    const rootNode: TreeNode = {
      gloss,
      display: paraphraseDisplay(gloss),
      children: [],
      marker,
      bold: true,
      role: 'root',
      warn_native_missing: rootWarnings.warn_native_missing,
      warn_target_missing: rootWarnings.warn_target_missing,
      warn_usage_missing: rootWarnings.warn_usage_missing,
      warn_parts_missing: rootWarnings.warn_parts_missing,
      state: determineGoalState(gloss, storage, native, target),
      goal_type: goalType,
      parentRef: `${situation.language}:${situation.slug || situation.content}`,
      viaField: 'children'
    }

    addLearnable(gloss, learnLang, true)

    const basePath = new Set<string>([rootKey])

    if (goalKind === 'understanding') {
      // Root translations (leaf only)
      rootNode.children.push(
        ...buildTranslationNodes(gloss, native, basePath, goalRootRef, rootKey, 'translations')
      )
      // Standard parts recursion starting at goal (skip usage on the root itself)
      rootNode.children.push(...buildPartsNodes(gloss, basePath, goalRootRef, learnLang, true))
    } else if (goalKind === 'procedural') {
      // Root translations to target, exclude paraphrase, each runs standard parts recursion
      for (const tRef of gloss.translations || []) {
        const [tLang] = tRef.split(':')
        if (normalizeLanguageCode(tLang) !== target) continue
        const tGloss = storage.resolveReference(tRef)
        if (!tGloss) continue
        if ((tGloss.tags || []).includes('eng:paraphrase')) continue

        const tWarnings = computeWarnings(tGloss, goalRootRef, {
          checkTranslationTo: native,
          checkParts: true,
          checkUsage: true
        })
        const tKey = glossKey(tGloss)
        const transNode: TreeNode = {
          gloss: tGloss,
          display: paraphraseDisplay(tGloss),
          children: [],
          marker: '',
          bold: false,
          role: 'translation',
          warn_native_missing: tWarnings.warn_native_missing,
          warn_target_missing: tWarnings.warn_target_missing,
          warn_usage_missing: tWarnings.warn_usage_missing,
          warn_parts_missing: tWarnings.warn_parts_missing,
          state: '',
          parentRef: rootKey,
          viaField: 'translations'
        }

        const branchPath = new Set<string>([rootKey, tKey])
        // Show translations back to native (leaf)
        transNode.children.push(
          ...buildTranslationNodes(tGloss, native, branchPath, goalRootRef, tKey, 'translations')
        )
        // Usage + parts recursion
        if (normalizeLanguageCode(tGloss.language) === target) {
          for (const uRef of tGloss.usage_examples || []) {
            const uGloss = storage.resolveReference(uRef)
            if (!uGloss) continue
            transNode.children.push(buildUsageNode(uGloss, branchPath, goalRootRef, tKey, 'usage_examples'))
          }
        }
        transNode.children.push(
          ...buildPartsNodes(tGloss, branchPath, goalRootRef, learnLang, true, {
            skipUsageForNode: false
          })
        )

        rootNode.children.push(transNode)
      }

      // Root parts, if present, also follow standard parts recursion
      if ((gloss.parts || []).length) {
        rootNode.children.push(
          ...buildPartsNodes(gloss, basePath, goalRootRef, learnLang, true, { skipUsageForNode: false })
        )
      }
    }

    nodes.push(rootNode)
  }

  return { nodes, stats }
}

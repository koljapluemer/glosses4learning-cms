import type { Gloss } from '../../main-process/storage/types'
import type { GlossStorage } from '../../main-process/storage/fsGlossStorage'

export const SPLIT_LOG_MARKER = 'SPLIT_CONSIDERED_UNNECESSARY'
export const TRANSLATION_IMPOSSIBLE_MARKER = 'TRANSLATION_CONSIDERED_IMPOSSIBLE'
export const USAGE_IMPOSSIBLE_MARKER = 'USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE'

function normalizeLanguageCode(code: string | null | undefined): string {
  return (code || '').trim().toLowerCase()
}

function glossRef(gloss: Gloss): string {
  return `${gloss.language}:${gloss.slug || gloss.content}`
}

function hasLog(gloss: Gloss, marker: string): boolean {
  const logs = gloss.logs || {}
  if (typeof logs !== 'object') return false
  return Object.values(logs).some((val) => String(val).includes(marker))
}

/**
 * Return normalized goal type for situation children or null if not a goal
 */
export function detectGoalType(
  gloss: Gloss,
  nativeLanguage: string,
  targetLanguage: string
): 'procedural' | 'understanding' | null {
  const lang = normalizeLanguageCode(gloss.language)
  const native = normalizeLanguageCode(nativeLanguage)
  const target = normalizeLanguageCode(targetLanguage)
  const tags = gloss.tags || []

  if (lang === native && tags.includes('eng:procedural-paraphrase-expression-goal')) {
    return 'procedural'
  }
  if (lang === target && tags.includes('eng:understand-expression-goal')) {
    return 'understanding'
  }
  return null
}

function usageExamples(storage: GlossStorage, g: Gloss): Gloss[] {
  const items: Gloss[] = []
  for (const ref of g.usage_examples || []) {
    const u = storage.resolveReference(ref)
    if (u) items.push(u)
  }
  return items
}

function parts(storage: GlossStorage, g: Gloss): Gloss[] {
  const items: Gloss[] = []
  for (const ref of g.parts || []) {
    const p = storage.resolveReference(ref)
    if (p) items.push(p)
  }
  return items
}

export type GoalState = 'red' | 'yellow'

export function paraphraseDisplay(gloss: Gloss): string {
  return gloss.content || ''
}

function resolvedTranslations(
  storage: GlossStorage,
  g: Gloss,
  lang: string,
  requireNonParaphrase: boolean = false
): Gloss[] {
  const matches: Gloss[] = []
  for (const ref of g.translations || []) {
    const [refLangRaw] = ref.split(':')
    const refLang = normalizeLanguageCode(refLangRaw)
    if (refLang !== lang) continue
    const tGloss = storage.resolveReference(ref)
    if (!tGloss) continue
    if (requireNonParaphrase && (tGloss.tags || []).includes('eng:paraphrase')) continue
    matches.push(tGloss)
  }
  return matches
}

type PartsCheckResult = {
  ok: boolean
  missingTranslations: string[]
  missingParts: string[]
  missingUsage: string[]
}

function standardPartsCheck(
  storage: GlossStorage,
  gloss: Gloss,
  native: string,
  target: string,
  path: Set<string>,
  options?: { skipUsageForRoot?: boolean }
): PartsCheckResult {
  const ref = glossRef(gloss)
  if (path.has(ref)) {
    return { ok: true, missingTranslations: [], missingParts: [], missingUsage: [] }
  }
  const nextPath = new Set(path)
  nextPath.add(ref)

  const res: PartsCheckResult = {
    ok: true,
    missingTranslations: [],
    missingParts: [],
    missingUsage: []
  }

  const lang = normalizeLanguageCode(gloss.language)
  const counterpart = lang === target ? native : lang === native ? target : null

  // parts presence or logged
  const hasParts = (gloss.parts || []).length > 0 || hasLog(gloss, SPLIT_LOG_MARKER)
  if (!hasParts) {
    res.ok = false
    res.missingParts.push(ref)
  }

  // translation requirement (to counterpart)
  if (counterpart) {
    const translations = resolvedTranslations(
      storage,
      gloss,
      counterpart,
      lang === native // only exclude paraphrase when translating native -> target
    )
    if (translations.length === 0 && !hasLog(gloss, `${TRANSLATION_IMPOSSIBLE_MARKER}:${counterpart}`)) {
      res.ok = false
      res.missingTranslations.push(ref)
    }
  }

  // usage requirement only for target-language nodes (unless explicitly skipped)
  const shouldCheckUsage = lang === target && !options?.skipUsageForRoot
  if (shouldCheckUsage) {
    const hasUsage = (gloss.usage_examples || []).length > 0 || hasLog(gloss, `${USAGE_IMPOSSIBLE_MARKER}:${target}`)
    if (!hasUsage) {
      res.ok = false
      res.missingUsage.push(ref)
    }
    for (const uGloss of usageExamples(storage, gloss)) {
      const uTrans = resolvedTranslations(storage, uGloss, native)
      if (uTrans.length === 0 && !hasLog(uGloss, `${TRANSLATION_IMPOSSIBLE_MARKER}:${native}`)) {
        res.ok = false
        res.missingTranslations.push(glossRef(uGloss))
      }
    }
  }

  // Recurse into parts
  for (const part of parts(storage, gloss)) {
    const child = standardPartsCheck(storage, part, native, target, nextPath)
    if (!child.ok) res.ok = false
    res.missingTranslations.push(...child.missingTranslations)
    res.missingParts.push(...child.missingParts)
    res.missingUsage.push(...child.missingUsage)
  }

  return res
}

/**
 * Compute RED/YELLOW for a goal in the context of native/target languages
 */
export function evaluateGoalState(
  gloss: Gloss,
  storage: GlossStorage,
  nativeLanguage: string,
  targetLanguage: string
): { state: GoalState; log: string } {
  const native = normalizeLanguageCode(nativeLanguage)
  const target = normalizeLanguageCode(targetLanguage)
  const goalLang = normalizeLanguageCode(gloss.language)
  const tags = gloss.tags || []

  const goalKind = detectGoalType(gloss, native, target)
  const goalRef = glossRef(gloss)
  const lines: string[] = [
    `goal=${goalRef}`,
    `kind=${goalKind || 'unknown'}`,
    `native=${native}`,
    `target=${target}`
  ]

  function section(title: string) {
    lines.push(`${title}:`)
  }

  function check(desc: string, passed: boolean, missing: string[] | null = null): boolean {
    lines.push(`- [${passed ? 'x' : ' '}] ${desc}`)
    if (!passed && missing && missing.length) {
      for (const item of missing) {
        lines.push(`  missing: ${item}`)
      }
    }
    return passed
  }

  let yellowOk = false

  if (goalKind === 'understanding') {
    section('requirements')
    const cLang = check('goal expression is in target language', goalLang === target, [goalRef])
    const goalNativeTrans = resolvedTranslations(storage, gloss, native)
    const cT1 = check(
      'goal has translation into native (or logged impossible)',
      goalNativeTrans.length > 0 || hasLog(gloss, `${TRANSLATION_IMPOSSIBLE_MARKER}:${native}`),
      goalNativeTrans.length < 1 ? [goalRef] : null
    )
    const partsCheck = standardPartsCheck(storage, gloss, native, target, new Set(), {
      skipUsageForRoot: true
    })
    const cParts = check(
      'goal and its parts satisfy standard parts recursion (parts + translations + usage-on-target)',
      partsCheck.ok,
      [...new Set([...partsCheck.missingParts, ...partsCheck.missingTranslations, ...partsCheck.missingUsage])]
    )
    yellowOk = cLang && cT1 && cParts
  } else if (goalKind === 'procedural') {
    section('requirements')
    const cLang = check('goal expression is in native language', goalLang === native, [goalRef])
    const cTag = check('goal tagged eng:paraphrase', tags.includes('eng:paraphrase'), [goalRef])
    const goalTargetTransGlosses = resolvedTranslations(storage, gloss, target, true)
    const cT1 = check(
      'goal has translation into target (non-paraphrase) or logged impossible',
      goalTargetTransGlosses.length > 0 || hasLog(gloss, `${TRANSLATION_IMPOSSIBLE_MARKER}:${target}`),
      goalTargetTransGlosses.length < 1 ? [goalRef] : null
    )
    const cPartsChecked = check(
      'goal checked for parts (has parts or logged unsplittable)',
      (gloss.parts || []).length > 0 || hasLog(gloss, SPLIT_LOG_MARKER),
      (gloss.parts || []).length > 0 || hasLog(gloss, SPLIT_LOG_MARKER) ? null : [goalRef]
    )

    let translationBranchesOk = true
    const missing: string[] = []
    for (const tGloss of goalTargetTransGlosses) {
      const branch = standardPartsCheck(storage, tGloss, native, target, new Set())
      if (!branch.ok) translationBranchesOk = false
      missing.push(...branch.missingParts, ...branch.missingTranslations, ...branch.missingUsage)
    }

    let rootPartsOk = true
    if ((gloss.parts || []).length) {
      const rootBranch = standardPartsCheck(storage, gloss, native, target, new Set(), {
        skipUsageForRoot: false
      })
      if (!rootBranch.ok) rootPartsOk = false
      missing.push(...rootBranch.missingParts, ...rootBranch.missingTranslations, ...rootBranch.missingUsage)
    }

    const branchesOk = translationBranchesOk && rootPartsOk
    check(
      'translations and any root parts satisfy standard parts recursion',
      branchesOk,
      branchesOk ? null : [...new Set(missing)]
    )

    yellowOk = cLang && cTag && cT1 && cPartsChecked && branchesOk
  } else {
    section('requirements')
    check('goal matches expected kind for native/target languages', false, [goalRef])
  }

  const state: GoalState = yellowOk ? 'yellow' : 'red'
  lines.push(`state=${state}`)
  return { state, log: lines.join('\n') }
}

export function determineGoalState(
  gloss: Gloss,
  storage: GlossStorage,
  nativeLanguage: string,
  targetLanguage: string
): GoalState {
  return evaluateGoalState(gloss, storage, nativeLanguage, targetLanguage).state
}

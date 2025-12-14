/**
 * Goal state detection and evaluation
 * Port of src/shared/tree.py:12-223
 */

import type { Gloss } from '../../../main-process/storage/types'
import type { GlossStorage } from '../../../main-process/storage/fsGlossStorage'

export const SPLIT_LOG_MARKER = 'SPLIT_CONSIDERED_UNNECESSARY'
export const TRANSLATION_IMPOSSIBLE_MARKER = 'TRANSLATION_CONSIDERED_IMPOSSIBLE'
export const USAGE_IMPOSSIBLE_MARKER = 'USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE'

function normalizeLanguageCode(code: string | null | undefined): string {
  return (code || '').trim().toLowerCase()
}

/**
 * Return normalized goal type for situation children or null if not a goal
 * Python ref: src/shared/tree.py:12-22
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

/**
 * Compute RED/YELLOW/GREEN for a goal in the context of native/target languages
 * and return a detailed log of checks.
 * Rules in doc/reference_what_is_a_valid_goal.md
 * Python ref: src/shared/tree.py:25-217
 */
export function evaluateGoalState(
  gloss: Gloss,
  storage: GlossStorage,
  nativeLanguage: string,
  targetLanguage: string
): { state: 'red' | 'yellow' | 'green'; log: string } {
  const native = normalizeLanguageCode(nativeLanguage)
  const target = normalizeLanguageCode(targetLanguage)
  const goalLang = normalizeLanguageCode(gloss.language)
  const tags = gloss.tags || []

  function translationRefs(
    g: Gloss,
    lang: string,
    requireNonParaphrase: boolean = false
  ): string[] {
    const matches: string[] = []
    for (const ref of g.translations || []) {
      const refLang = ref.split(':')[0]?.trim().toLowerCase()
      if (refLang !== lang) continue

      const tGloss = storage.resolveReference(ref)
      if (!tGloss) continue

      if (requireNonParaphrase && (tGloss.tags || []).includes('eng:paraphrase')) {
        continue
      }
      matches.push(`${tGloss.language}:${tGloss.slug || tGloss.content}`)
    }
    return matches
  }

  function parts(): Gloss[] {
    const items: Gloss[] = []
    for (const ref of gloss.parts || []) {
      const p = storage.resolveReference(ref)
      if (p) items.push(p)
    }
    return items
  }

  function translationsTo(
    gl: Gloss,
    lang: string,
    requireNonParaphrase: boolean = false
  ): Gloss[] {
    const matches: Gloss[] = []
    for (const ref of gl.translations || []) {
      const refLang = ref.split(':')[0]?.trim().toLowerCase()
      if (refLang !== lang) continue

      const tGloss = storage.resolveReference(ref)
      if (!tGloss) continue

      if (requireNonParaphrase && (tGloss.tags || []).includes('eng:paraphrase')) {
        continue
      }
      matches.push(tGloss)
    }
    return matches
  }

  const goalKind = detectGoalType(gloss, native, target)
  const goalRef = `${gloss.language}:${gloss.slug || gloss.content}`
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
    if (!passed && missing) {
      for (const item of missing) {
        lines.push(`  missing: ${item}`)
      }
    }
    return passed
  }

  let yellowOk = false
  let greenOk = false

  if (goalKind === 'understanding') {
    section('yellow_requirements')
    const cLang = check('goal expression is in target language', goalLang === target, [goalRef])
    const goalNativeTrans = translationRefs(gloss, native)
    const cT1 = check(
      'goal has >=1 translation into native',
      goalNativeTrans.length >= 1,
      goalNativeTrans.length < 1 ? [goalRef] : null
    )
    const partsList = parts()
    const cParts = check('goal has parts', partsList.length > 0, partsList.length === 0 ? [goalRef] : null)
    const missingPartsTrans: string[] = []
    for (const part of partsList) {
      const partTrans = translationRefs(part, native)
      if (partTrans.length < 1) {
        missingPartsTrans.push(`${part.language}:${part.slug || part.content}`)
      }
    }
    const cPartsTrans = check(
      'each part has >=1 translation to native',
      missingPartsTrans.length === 0,
      missingPartsTrans.length > 0 ? missingPartsTrans : null
    )
    yellowOk = cLang && cT1 && cParts && cPartsTrans

    section('green_requirements')
    if (yellowOk) {
      const cT2 = check(
        'goal has >=2 translations into native',
        goalNativeTrans.length >= 2,
        [goalRef]
      )
      const missingPartsUsage: string[] = []
      for (const part of partsList) {
        const usableExamples: string[] = []
        const lackingExamples: string[] = []
        for (const uRef of part.usage_examples || []) {
          const usageGloss = storage.resolveReference(uRef)
          if (!usageGloss) {
            lackingExamples.push(`${uRef} (missing gloss)`)
            continue
          }
          if (translationRefs(usageGloss, native).length > 0) {
            usableExamples.push(`${usageGloss.language}:${usageGloss.slug || usageGloss.content}`)
          } else {
            lackingExamples.push(`${usageGloss.language}:${usageGloss.slug || usageGloss.content}`)
          }
        }
        if (usableExamples.length < 2) {
          const detail = `${part.language}:${part.slug || part.content} (usable: ${usableExamples.join(', ') || 'none'}; lacking native translation on: ${lackingExamples.join(', ') || 'none'})`
          missingPartsUsage.push(detail)
        }
      }
      const cPartsUsage = check(
        'each part has >=2 usage examples translated once to native',
        missingPartsUsage.length === 0,
        missingPartsUsage.length > 0 ? missingPartsUsage : null
      )
      greenOk = cT2 && cPartsUsage
    } else {
      check('reach yellow first', false, [goalRef])
    }
  } else if (goalKind === 'procedural') {
    section('yellow_requirements')
    const cLang = check('goal expression is in native language', goalLang === native, [goalRef])
    const cTag = check('goal tagged eng:paraphrase', tags.includes('eng:paraphrase'), [goalRef])
    const goalTargetTransGlosses = translationsTo(gloss, target)
    const cT1 = check(
      'goal has >=1 translation into target',
      goalTargetTransGlosses.length >= 1,
      [goalRef]
    )
    // For procedural paraphrases: do not require parts on the goal itself.
    // Require each translated target expression to have parts, and those parts to translate back to native.
    const missingParts: string[] = []
    const missingPartsTrans: string[] = []
    for (const tGloss of goalTargetTransGlosses) {
      const tParts = tGloss.parts || []
      if (tParts.length === 0) {
        missingParts.push(`${tGloss.language}:${tGloss.slug || tGloss.content}`)
        continue
      }
      for (const partRef of tParts) {
        const part = storage.resolveReference(partRef)
        if (!part) {
          missingPartsTrans.push(`${partRef} (missing gloss)`)
          continue
        }
        const backTrans = translationRefs(part, native)
        if (backTrans.length < 1) {
          missingPartsTrans.push(`${part.language}:${part.slug || part.content}`)
        }
      }
    }
    const cParts = check('each target translation has parts', missingParts.length === 0, missingParts.length > 0 ? missingParts : null)
    const cPartsTrans = check(
      'each part of each target translation has >=1 translation to native',
      missingPartsTrans.length === 0,
      missingPartsTrans.length > 0 ? missingPartsTrans : null
    )
    yellowOk = cLang && cTag && cT1 && cParts && cPartsTrans

    section('green_requirements')
    if (yellowOk) {
      const cT2 = check(
        'goal has >=2 translations into target',
        goalTargetTransGlosses.length >= 2,
        [goalRef]
      )
      greenOk = cT2
    } else {
      check('reach yellow first', false, [goalRef])
    }
  } else {
    section('yellow_requirements')
    check('goal matches expected kind for native/target languages', false, [goalRef])
    section('green_requirements')
    check('reach yellow first', false, [goalRef])
  }

  const state = greenOk ? 'green' : yellowOk ? 'yellow' : 'red'
  lines.push(`state=${state}`)
  return { state, log: lines.join('\n') }
}

/**
 * Backward-compatible helper returning only the state
 * Python ref: src/shared/tree.py:220-222
 */
export function determineGoalState(
  gloss: Gloss,
  storage: GlossStorage,
  nativeLanguage: string,
  targetLanguage: string
): 'red' | 'yellow' | 'green' {
  return evaluateGoalState(gloss, storage, nativeLanguage, targetLanguage).state
}

/**
 * Wrap paraphrases in [brackets] for display
 * Python ref: src/shared/tree.py:225-231
 */
export function paraphraseDisplay(gloss: Gloss): string {
  return gloss.content || ''
}

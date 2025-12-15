import { Agent, run } from '@openai/agents'
import { OpenAIChatCompletionsModel } from '@openai/agents-openai'
import OpenAI from 'openai'
import type { Gloss } from '../../../main-process/storage/types'
import { loadLanguages } from '../../entities/languages/loader'
import { logAi } from '../../entities/ai/aiLogger'

const MODEL = 'gpt-4o-mini'
const TEMP_TRANSLATION = 0.2
const TEMP_GENERATION = 0.2
const TEMP_JUDGE = 0.0

type TranslationMode = 'toNative' | 'toTarget' | 'paraphraseToTarget'

export interface Suggestion {
  glossRef: string
  suggestions: string[]
}

interface GenerationOptions {
  context?: string
  count?: number
}

async function getAiNote(language: string): Promise<string | null> {
  const langs = await loadLanguages()
  const hit = langs.find((l) => l.isoCode === language)
  return hit?.aiNote ?? null
}

async function fetchGlosses(refs: string[]): Promise<Gloss[]> {
  const results: Gloss[] = []
  for (const ref of refs.slice(0, 50)) {
    const g = await window.electronAPI.gloss.resolveRef(ref)
    if (g) results.push(g)
  }
  return results
}

function translationPrompt(
  mode: TranslationMode,
  glosses: Gloss[],
  native: string,
  target: string,
  aiNote: string | null,
  options?: GenerationOptions
) {
  const bullets = glosses.map((g) => `- ${g.content}`).join('\n')
  const count = options?.count ?? 2
  const contextLine = options?.context ? `${options.context}\n\n` : ''
  const aiNoteText = aiNote ? `Language notes: ${aiNote}\n\n` : ''

  if (mode === 'paraphraseToTarget') {
    return `${contextLine}${aiNoteText}You are a specialized language assistant for translating communicative goals (paraphrases) into actual expressions.

CRITICAL: The input is NOT a phrase to translate literally. It is a COMMUNICATIVE GOAL describing what a learner wants to express.

Your task:
- Find the ACTUAL ways native speakers would EXPRESS this goal in the target language (${target})
- Return real phrases/expressions, NOT literal word-for-word translations
- Include usage notes ONLY when expressions have important context differences

Provide ${count} expressions for each item.

Items:
${bullets}

Return JSON { "items": [ { "source": "<content>", "translations": [ {"text": str, "note": str}, ... ] } ] }. Always include "note" (empty string if none).`
  }

  if (mode === 'toNative') {
    return `${contextLine}${aiNoteText}Translate these ${target} glosses into ${native}.
Provide 2-4 concise, practical translations per gloss (JSON only).

Items:
${bullets}

Return JSON { "items": [ { "source": "<content>", "translations": ["..."] } ] }.`
  }

  return `${contextLine}${aiNoteText}Translate these ${native} glosses into ${target}.
Provide 2-4 natural translations per gloss with an optional usage note (empty string if none).

Items:
${bullets}

Return JSON { "items": [ { "source": "<content>", "translations": [ {"text": str, "note": str}, ... ] } ] }.`
}

function partsPrompt(glosses: Gloss[], aiNote: string | null, options?: GenerationOptions) {
  const bullets = glosses.map((g) => `- ${g.content}`).join('\n')
  const contextLine = options?.context ? `${options.context}\n\n` : ''
  const aiNoteText = aiNote ? `Language notes: ${aiNote}\n\n` : ''
  return `${contextLine}${aiNoteText}You are a concise linguistic decomposition assistant.

Break expressions into learnable component parts - words or meaningful sub-expressions.

Take each expression below and break it up into parts that can be learned on their own.
Each returned item must be a meaningful standalone item.
If an input cannot be split into meaningful part, return an empty array for this item.

Return JSON with 'parts' array for each source.

Items:
${bullets}

Return JSON { "items": [ { "source": "<content>", "parts": ["..."] } ] }`
}

function usagePrompt(glosses: Gloss[], aiNote: string | null, options?: GenerationOptions) {
  const bullets = glosses.map((g) => `- ${g.content} (${g.language})`).join('\n')
  const count = options?.count ?? 2
  const contextLine = options?.context ? `${options.context}\n\n` : ''
  const aiNoteText = aiNote ? `Language notes: ${aiNote}\n\n` : ''
  return `${contextLine}${aiNoteText}You generate concise usage example sentences for language learning.

Create natural, practical sentences that demonstrate how the word or phrase is used in context.
Prefer short sentences, 3-5 words is ideal.

Generate ${count} example sentences that use the word/phrase.

Items:
${bullets}

Return JSON { "items": [ { "source": "<content>", "usages": ["..."] } ] }`
}

function splitJudgePrompt(glosses: Gloss[]) {
  const bullets = glosses.map((g) => `- ${g.content}`).join('\n')
  return `You judge if expressions can be split into learnable parts.

Single words CANNOT be split and should return false!
Do not return true if all a word can be split into is letters or syllables with no own meaning.
Multi-word phrases or expressions can be split into component words or sub-expressions (true).

For each gloss below, judge true/false.

Glosses:
${bullets}

Return JSON { "items": [ { "source": "<content>", "splittable": true/false } ] }`
}

function usageJudgePrompt(glosses: Gloss[]) {
  const bullets = glosses.map((g) => `- ${g.content} (${g.language})`).join('\n')
  return `You judge whether glosses are suitable for usage examples.

Words and short phrases can usefully be demonstrated in example sentences.
Complete sentences or long expressions cannot - they ARE the examples.

For each gloss below, return true if it's a word/short phrase that can be used in an example sentence, false otherwise.

Glosses:
${bullets}

Return JSON { "items": [ { "source": "<content>", "ok": true/false } ] }`
}

async function runJsonAgent(apiKey: string, prompt: string, temperature: number): Promise<string> {
  const client = new OpenAI({ apiKey, dangerouslyAllowBrowser: true })
  const agent = new Agent({
    name: 'json-runner',
    instructions: 'Return ONLY valid JSON matching the user request. No prose.',
    model: new OpenAIChatCompletionsModel(client, MODEL),
    modelSettings: { temperature }
  })
  const result = await run(agent, prompt)
  return (result.finalOutput ?? '').toString().trim()
}

async function runCompletion(
  apiKey: string,
  prompt: string,
  temperature: number
): Promise<Record<string, string[]>> {
  const content = (await runJsonAgent(apiKey, prompt, temperature)) || '{}'
  const parsed = JSON.parse(content)
  const items = parsed.items || []
  const map = new Map<string, string[]>()
  for (const item of items) {
    const source = String(item.source || '').trim()
    if (!source) continue
    const raw =
      item.translations ||
      item.parts ||
      item.usages ||
      []
    const vals: string[] = []
    for (const v of raw || []) {
      if (typeof v === 'string' && v.trim()) {
        vals.push(v.trim())
      } else if (v && typeof v === 'object' && typeof v.text === 'string' && v.text.trim()) {
        vals.push(v.text.trim())
      }
    }
    map.set(source, vals)
  }
  return Object.fromEntries(map)
}

async function runJudge(apiKey: string, prompt: string): Promise<Set<string>> {
  const content = (await runJsonAgent(apiKey, prompt, TEMP_JUDGE)) || '{}'
  const parsed = JSON.parse(content)
  const items = parsed.items || parsed || []
  const okSet = new Set<string>()
  if (Array.isArray(items)) {
    for (const item of items) {
      const source = String(item.source || '').trim()
      const decision = item.splittable === true || item.ok === true
      if (source && decision) {
        okSet.add(source)
      }
    }
  } else if (items && typeof items === 'object') {
    for (const [source, decision] of Object.entries(items)) {
      if (decision === true) {
        okSet.add(source)
      }
    }
  }
  return okSet
}

function mapSuggestions(glosses: Gloss[], bag: Record<string, string[]>): Suggestion[] {
  const res: Suggestion[] = []
  for (const g of glosses) {
    const vals = bag[g.content] || []
    if (vals.length) {
      res.push({
        glossRef: `${g.language}:${g.slug}`,
        suggestions: vals
      })
    }
  }
  return res
}

export async function generateTranslations(
  apiKey: string,
  mode: TranslationMode,
  refs: string[],
  native: string,
  target: string,
  options?: GenerationOptions
): Promise<Suggestion[]> {
  const started = performance.now()
  if (!refs.length) return []
  try {
    const glosses = await fetchGlosses(refs.slice(0, 25))
    if (!glosses.length) return []
    const note =
      mode === 'toNative'
        ? await getAiNote(native)
        : await getAiNote(target)
    const prompt = translationPrompt(mode, glosses, native, target, note, options)
    const bag = await runCompletion(apiKey, prompt, TEMP_TRANSLATION)
    const suggestions = mapSuggestions(glosses, bag)
    const suggestionDetails = suggestions.map((s) => ({
      ref: s.glossRef,
      count: s.suggestions.length,
      suggestions: s.suggestions
    }))
    await logAi('generateTranslations', refs, {
      mode,
      promptLength: prompt.length,
      suggestionSets: suggestions.length,
      totalSuggestions: suggestions.reduce((acc, s) => acc + s.suggestions.length, 0),
      suggestions: suggestionDetails,
      durationMs: Math.round(performance.now() - started)
    })
    return suggestions
  } catch (err) {
    await logAi('generateTranslationsError', refs, {
      mode,
      error: err instanceof Error ? err.message : String(err),
      durationMs: Math.round(performance.now() - started)
    })
    throw err
  }
}

export async function generateParts(
  apiKey: string,
  refs: string[],
  options?: GenerationOptions
): Promise<Suggestion[]> {
  const started = performance.now()
  if (!refs.length) return []
  try {
    const glosses = await fetchGlosses(refs.slice(0, 20))
    if (!glosses.length) return []
    const judgeOk = await runJudge(apiKey, splitJudgePrompt(glosses))
    const rejected = glosses.filter((g) => !judgeOk.has(g.content))
    await logAi('generateParts.judge', refs, {
      okRefs: glosses.filter((g) => judgeOk.has(g.content)).map((g) => `${g.language}:${g.slug}`),
      rejectedRefs: rejected.map((g) => `${g.language}:${g.slug}`),
      durationMs: Math.round(performance.now() - started)
    })
    for (const gloss of rejected) {
      await window.electronAPI.gloss.markLog(
        `${gloss.language}:${gloss.slug}`,
        'SPLIT_CONSIDERED_UNNECESSARY'
      )
    }
    const filtered = glosses.filter((g) => judgeOk.has(g.content))
    if (!filtered.length) return []
    const aiNote = await getAiNote(filtered[0].language)
    const prompt = partsPrompt(filtered, aiNote, options)
    const bag = await runCompletion(apiKey, prompt, TEMP_GENERATION)
    const suggestions = mapSuggestions(filtered, bag)
    const suggestionDetails = suggestions.map((s) => ({
      ref: s.glossRef,
      count: s.suggestions.length,
      suggestions: s.suggestions
    }))
    await logAi('generateParts', refs, {
      judgedOk: filtered.length,
      rejected: rejected.length,
      promptLength: prompt.length,
      suggestionSets: suggestions.length,
      totalSuggestions: suggestions.reduce((acc, s) => acc + s.suggestions.length, 0),
      suggestions: suggestionDetails,
      durationMs: Math.round(performance.now() - started)
    })
    return suggestions
  } catch (err) {
    await logAi('generatePartsError', refs, {
      error: err instanceof Error ? err.message : String(err),
      durationMs: Math.round(performance.now() - started)
    })
    throw err
  }
}

export async function generateUsage(
  apiKey: string,
  refs: string[],
  options?: GenerationOptions
): Promise<Suggestion[]> {
  const started = performance.now()
  if (!refs.length) return []
  try {
    const glosses = await fetchGlosses(refs.slice(0, 20))
    if (!glosses.length) return []
    const judgeOk = await runJudge(apiKey, usageJudgePrompt(glosses))
    const rejected = glosses.filter((g) => !judgeOk.has(g.content))
    await logAi('generateUsage.judge', refs, {
      okRefs: glosses.filter((g) => judgeOk.has(g.content)).map((g) => `${g.language}:${g.slug}`),
      rejectedRefs: rejected.map((g) => `${g.language}:${g.slug}`),
      durationMs: Math.round(performance.now() - started)
    })
    for (const gloss of rejected) {
      await window.electronAPI.gloss.markLog(
        `${gloss.language}:${gloss.slug}`,
        `USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE:${gloss.language}`
      )
    }
    const filtered = glosses.filter((g) => judgeOk.has(g.content))
    if (!filtered.length) return []
    const aiNote = await getAiNote(filtered[0].language)
    const prompt = usagePrompt(filtered, aiNote, options)
    const bag = await runCompletion(apiKey, prompt, TEMP_GENERATION)
    const suggestions = mapSuggestions(filtered, bag)
    const suggestionDetails = suggestions.map((s) => ({
      ref: s.glossRef,
      count: s.suggestions.length,
      suggestions: s.suggestions
    }))
    await logAi('generateUsage', refs, {
      judgedOk: filtered.length,
      rejected: rejected.length,
      promptLength: prompt.length,
      suggestionSets: suggestions.length,
      totalSuggestions: suggestions.reduce((acc, s) => acc + s.suggestions.length, 0),
      suggestions: suggestionDetails,
      durationMs: Math.round(performance.now() - started)
    })
    return suggestions
  } catch (err) {
    await logAi('generateUsageError', refs, {
      error: err instanceof Error ? err.message : String(err),
      durationMs: Math.round(performance.now() - started)
    })
    throw err
  }
}

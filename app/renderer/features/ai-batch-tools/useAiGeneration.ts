import { Agent, run } from '@openai/agents'
import { OpenAIChatCompletionsModel, setDefaultOpenAIKey } from '@openai/agents-openai'
import type { Gloss } from '../../../main-process/storage/types'

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
  options?: GenerationOptions
) {
  const bullets = glosses.map((g) => `- ${g.content}`).join('\n')
  const count = options?.count ?? 2
  const contextLine = options?.context ? `Context: ${options.context}\n` : ''

  if (mode === 'paraphraseToTarget') {
    return `${contextLine}You receive paraphrased procedural descriptions written in the learner's native language (${native}). 
Produce up to ${count} NATURAL target-language (${target}) expressions the learner would actually SAY to achieve that intent.
Rules:
- Output only real target expressions, no brackets, no explanations.
- Keep them concise and idiomatic.
- Avoid literal translation of paraphrase phrasing.
Items:
${bullets}
Return JSON { "items": [ { "source": "<content>", "translations": ["..."] } ] }.`
  }

  if (mode === 'toNative') {
    return `${contextLine}Translate each target-language expression into the learner's native language (${native}). Provide up to ${count} natural equivalents.
Items:
${bullets}
Return JSON { "items": [ { "source": "<content>", "translations": ["..."] } ] }.`
  }

  return `${contextLine}Translate each native-language expression into target language (${target}). Provide up to ${count} concise, natural target expressions.
Items:
${bullets}
Return JSON { "items": [ { "source": "<content>", "translations": ["..."] } ] }.`
}

function partsPrompt(glosses: Gloss[], options?: GenerationOptions) {
  const bullets = glosses.map((g) => `- ${g.content}`).join('\n')
  const count = options?.count ?? 3
  const contextLine = options?.context ? `Context: ${options.context}\n` : ''
  return `${contextLine}Split each gloss into 2-${count} constituent parts (same language). Avoid duplicates, keep short.
Items:
${bullets}
Return JSON { "items": [ { "source": "<content>", "parts": ["..."] } ] }`
}

function usagePrompt(glosses: Gloss[], options?: GenerationOptions) {
  const bullets = glosses.map((g) => `- ${g.content} (${g.language})`).join('\n')
  const count = options?.count ?? 2
  const contextLine = options?.context ? `Context: ${options.context}\n` : ''
  return `${contextLine}Generate ${count} short usage examples in the same language for each gloss. Keep natural and brief.
Items:
${bullets}
Return JSON { "items": [ { "source": "<content>", "usages": ["..."] } ] }`
}

function splitJudgePrompt(glosses: Gloss[]) {
  const bullets = glosses.map((g) => `- ${g.content}`).join('\n')
  return `Decide if each gloss can be meaningfully split into parts. Answer yes/no.
Items:
${bullets}
Return JSON { "items": [ { "source": "<content>", "splittable": true/false } ] }`
}

function usageJudgePrompt(glosses: Gloss[]) {
  const bullets = glosses.map((g) => `- ${g.content} (${g.language})`).join('\n')
  return `Decide if each gloss is suitable for generating usage examples. Answer yes/no.
Criteria: expressions or parts that appear in sentences; skip function words.
Items:
${bullets}
Return JSON { "items": [ { "source": "<content>", "ok": true/false } ] }`
}

async function runJsonAgent(apiKey: string, prompt: string, temperature: number): Promise<string> {
  setDefaultOpenAIKey(apiKey)
  const agent = new Agent({
    name: 'json-runner',
    instructions: 'Return ONLY valid JSON matching the user request. No prose.',
    model: new OpenAIChatCompletionsModel({ model: MODEL, temperature })
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
    const vals =
      (item.translations || item.parts || item.usages || []).filter(
        (v: unknown) => typeof v === 'string' && v.trim()
      ) || []
    map.set(source, vals.map((v: string) => v.trim()))
  }
  return map as Record<string, string[]>
}

async function runJudge(apiKey: string, prompt: string): Promise<Set<string>> {
  const content = (await runJsonAgent(apiKey, prompt, TEMP_JUDGE)) || '{}'
  const parsed = JSON.parse(content)
  const items = parsed.items || []
  const okSet = new Set<string>()
  for (const item of items) {
    const source = String(item.source || '').trim()
    const decision = item.splittable === true || item.ok === true
    if (source && decision) {
      okSet.add(source)
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
  if (!refs.length) return []
  const glosses = await fetchGlosses(refs.slice(0, 25))
  if (!glosses.length) return []
  const prompt = translationPrompt(mode, glosses, native, target, options)
  const bag = await runCompletion(apiKey, prompt, TEMP_TRANSLATION)
  return mapSuggestions(glosses, bag)
}

export async function generateParts(
  apiKey: string,
  refs: string[],
  options?: GenerationOptions
): Promise<Suggestion[]> {
  if (!refs.length) return []
  const glosses = await fetchGlosses(refs.slice(0, 20))
  if (!glosses.length) return []
  const judgeOk = await runJudge(apiKey, splitJudgePrompt(glosses))
  const rejected = glosses.filter((g) => !judgeOk.has(g.content))
  for (const gloss of rejected) {
    await window.electronAPI.gloss.markLog(
      `${gloss.language}:${gloss.slug}`,
      'SPLIT_CONSIDERED_UNNECESSARY'
    )
  }
  const filtered = glosses.filter((g) => judgeOk.has(g.content))
  if (!filtered.length) return []
  const prompt = partsPrompt(filtered, options)
  const bag = await runCompletion(apiKey, prompt, TEMP_GENERATION)
  return mapSuggestions(filtered, bag)
}

export async function generateUsage(
  apiKey: string,
  refs: string[],
  options?: GenerationOptions
): Promise<Suggestion[]> {
  if (!refs.length) return []
  const glosses = await fetchGlosses(refs.slice(0, 20))
  if (!glosses.length) return []
  const judgeOk = await runJudge(apiKey, usageJudgePrompt(glosses))
  const rejected = glosses.filter((g) => !judgeOk.has(g.content))
  for (const gloss of rejected) {
    await window.electronAPI.gloss.markLog(
      `${gloss.language}:${gloss.slug}`,
      `USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE:${gloss.language}`
    )
  }
  const filtered = glosses.filter((g) => judgeOk.has(g.content))
  if (!filtered.length) return []
  const prompt = usagePrompt(filtered, options)
  const bag = await runCompletion(apiKey, prompt, TEMP_GENERATION)
  return mapSuggestions(filtered, bag)
}

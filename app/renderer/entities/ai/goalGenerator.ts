/**
 * AI-powered goal generation using @openai/agents
 * Ports from agent/tools/llm/generate_*_goals.py
 */

import { Agent, run } from '@openai/agents'
import { OpenAIChatCompletionsModel } from '@openai/agents-openai'
import OpenAI from 'openai'
import { logAi } from './aiLogger'

const MODEL_NAME = 'gpt-4o-mini'
const TEMPERATURE_CREATIVE = 0.7
const SYSTEM_UNDERSTANDING =
  'You create expressions in the target language that a learner needs to understand in various situations.'
const SYSTEM_PROCEDURAL =
  'You create practical expression goals a learner wants to express in the native language.'

interface GeneratedGoals {
  goals: string[]
  count: number
  message: string
}

async function runJsonList(apiKey: string, prompt: string): Promise<string[]> {
  const started = performance.now()
  const client = new OpenAI({ apiKey, dangerouslyAllowBrowser: true })
  const agent = new Agent({
    name: 'goal-generator',
    instructions: 'Return ONLY JSON with a top-level "goals" array of strings. No prose.',
    model: new OpenAIChatCompletionsModel(client, MODEL_NAME),
    modelSettings: { temperature: TEMPERATURE_CREATIVE }
  })
  try {
    const result = await run(agent, prompt)
    const content = (result.finalOutput ?? '').toString().trim() || '{}'
    const parsed = JSON.parse(content)
    const goals = (parsed.goals || []).filter((g: unknown) => typeof g === 'string' && g.trim())
    const normalized = goals.map((g: string) => g.trim())
    await logAi('generateGoals.success', [], {
      promptLength: prompt.length,
      goalsCount: normalized.length,
      durationMs: Math.round(performance.now() - started)
    })
    return normalized
  } catch (err) {
    await logAi('generateGoals.error', [], {
      promptLength: prompt.length,
      error: err instanceof Error ? err.message : String(err),
      durationMs: Math.round(performance.now() - started)
    })
    throw err
  }
}

/**
 * Generate understanding goals for a situation
 */
export async function generateUnderstandingGoals(
  apiKey: string,
  situationContent: string,
  targetLanguage: string,
  numGoals: number = 5,
  extraContext: string = ''
): Promise<GeneratedGoals> {
  const contextText = extraContext ? `Additional context: ${extraContext}` : ''
  const userPrompt = `${SYSTEM_UNDERSTANDING}

Generate ${numGoals} expressions in ${targetLanguage} for the situation: "${situationContent}".

These are things a learner might HEAR or encounter in ${targetLanguage} and need to UNDERSTAND.
Make sure these are NOT things the learner may want to say themselves, but EXCLUSIVELY things the learner may HEAR FROM OTHERS.
E.g., if the context is 'order at a restaurant', the learner will never HEAR "Die Rechnung, bitte", so DO NOT INCLUDE SUCH EXAMPLES. 

Examples:
- Questions people might ask them
- Statements they might hear
- Signs or announcements they might read

Requirements:
- Natural, native expressions in ${targetLanguage}
- Relevant to the situation
- Practical and commonly used

${contextText}

Return JSON with a 'goals' array of strings.`

  const goals = await runJsonList(apiKey, userPrompt)

  return {
    goals,
    count: goals.length,
    message: `Generated ${goals.length} understanding goals.`
  }
}

/**
 * Generate procedural goals for a situation
 * Port of agent/tools/llm/generate_procedural_goals.py:13-150
 */
export async function generateProceduralGoals(
  apiKey: string,
  situationContent: string,
  nativeLanguage: string,
  targetLanguage: string,
  numGoals: number = 5,
  extraContext: string = ''
): Promise<GeneratedGoals> {
  const contextText = extraContext ? `Additional context: ${extraContext}` : ''
  const userPrompt = `${SYSTEM_PROCEDURAL}

Generate ${numGoals} paraphrased expressions in ${nativeLanguage} for the situation: "${situationContent}".

These are procedural descriptions in the learner's native language of things they might want to express in ${targetLanguage}.

Make sure these are sepcific enough to be actually translatable into queries in a foreign language.
E.g. do not include something vague like "share a personal story", because that is not something that can actually be translated.

Requirements:
- Formulate as standalone flashcards that make sense on their own
- Use descriptors instead of dangling pronouns (e.g., "ask your friend" not "ask them")
- Examples: "ask where something is", "express gratitude", "ask if the person you're cooking with needs help"

${contextText}

Return JSON with a 'goals' array of strings.`

  const goals = await runJsonList(apiKey, userPrompt)

  return {
    goals,
    count: goals.length,
    message: `Generated ${goals.length} procedural goals.`
  }
}

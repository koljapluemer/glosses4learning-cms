/**
 * AI-powered goal generation using @openai/agents
 * Ports from agent/tools/llm/generate_*_goals.py
 */

import { Agent, run } from '@openai/agents'
import { OpenAIChatCompletionsModel, setDefaultOpenAIKey } from '@openai/agents-openai'

const MODEL_NAME = 'gpt-4o-mini'
const TEMPERATURE_CREATIVE = 0.7

interface GeneratedGoals {
  goals: string[]
  count: number
  message: string
}

async function runJsonList(
  apiKey: string,
  prompt: string
): Promise<string[]> {
  setDefaultOpenAIKey(apiKey)
  const agent = new Agent({
    name: 'goal-generator',
    instructions: 'Return ONLY JSON with a top-level "goals" array of strings. No prose.',
    model: new OpenAIChatCompletionsModel({ model: MODEL_NAME, temperature: TEMPERATURE_CREATIVE })
  })
  const result = await run(agent, prompt)
  const content = (result.finalOutput ?? '').toString().trim() || '{}'
  const parsed = JSON.parse(content)
  const goals = (parsed.goals || []).filter((g: unknown) => typeof g === 'string' && g.trim())
  return goals.map((g: string) => g.trim())
}

/**
 * Generate understanding goals for a situation
 * Port of agent/tools/llm/generate_understanding_goals.py:13-148
 */
export async function generateUnderstandingGoals(
  apiKey: string,
  situationContent: string,
  targetLanguage: string,
  numGoals: number = 5,
  extraContext: string = ''
): Promise<GeneratedGoals> {
  const contextText = extraContext ? `Additional context: ${extraContext}` : ''
  const userPrompt = `Generate ${numGoals} expressions in ${targetLanguage} for the situation: "${situationContent}".

These are things a learner might HEAR or encounter in ${targetLanguage} and need to UNDERSTAND.

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
  const userPrompt = `Generate ${numGoals} paraphrased expressions in ${nativeLanguage} for the situation: "${situationContent}".

These are procedural descriptions in the learner's native language of things they might want to express in ${targetLanguage}.

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

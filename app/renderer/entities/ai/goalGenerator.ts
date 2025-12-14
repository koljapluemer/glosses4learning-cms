/**
 * AI-powered goal generation using OpenAI
 * Ports from agent/tools/llm/generate_*_goals.py
 */

import OpenAI from 'openai'

const MODEL_NAME = 'gpt-4o-mini'
const TEMPERATURE_CREATIVE = 0.7

interface GeneratedGoals {
  goals: string[]
  count: number
  message: string
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
  const client = new OpenAI({ apiKey, dangerouslyAllowBrowser: true })

  const systemPrompt = 'You create expressions in the target language that a learner needs to understand in various situations.'

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

  const response = await client.chat.completions.create({
    model: MODEL_NAME,
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: userPrompt }
    ],
    temperature: TEMPERATURE_CREATIVE,
    max_tokens: 500,
    response_format: {
      type: 'json_schema',
      json_schema: {
        name: 'goal_list',
        schema: {
          type: 'object',
          properties: {
            goals: {
              type: 'array',
              items: { type: 'string' }
            }
          },
          required: ['goals'],
          additionalProperties: false
        },
        strict: true
      }
    }
  })

  const content = response.choices[0]?.message?.content?.trim() || '{}'
  const parsed = JSON.parse(content)
  const goals = (parsed.goals || []).filter((g: unknown) => typeof g === 'string' && g.trim()).map((g: string) => g.trim())

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
  const client = new OpenAI({ apiKey, dangerouslyAllowBrowser: true })

  const systemPrompt = 'You create practical expression goals a learner wants to express in the native language.'

  const contextText = extraContext ? `Additional context: ${extraContext}` : ''
  const userPrompt = `Generate ${numGoals} paraphrased expressions in ${nativeLanguage} for the situation: "${situationContent}".

These are procedural descriptions in the learner's native language of things they might want to express in ${targetLanguage}.

Requirements:
- Formulate as standalone flashcards that make sense on their own
- Use descriptors instead of dangling pronouns (e.g., "ask your friend" not "ask them")
- Examples: "ask where something is", "express gratitude", "ask if the person you're cooking with needs help"

${contextText}

Return JSON with a 'goals' array of strings.`

  const response = await client.chat.completions.create({
    model: MODEL_NAME,
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: userPrompt }
    ],
    temperature: TEMPERATURE_CREATIVE,
    max_tokens: 500,
    response_format: {
      type: 'json_schema',
      json_schema: {
        name: 'goal_list',
        schema: {
          type: 'object',
          properties: {
            goals: {
              type: 'array',
              items: { type: 'string' }
            }
          },
          required: ['goals'],
          additionalProperties: false
        },
        strict: true
      }
    }
  })

  const content = response.choices[0]?.message?.content?.trim() || '{}'
  const parsed = JSON.parse(content)
  const goals = (parsed.goals || []).filter((g: unknown) => typeof g === 'string' && g.trim()).map((g: string) => g.trim())

  return {
    goals,
    count: goals.length,
    message: `Generated ${goals.length} procedural goals.`
  }
}

import OpenAI from 'openai'
import { logAi } from './aiLogger'

const MODEL_NAME = 'gpt-4o-mini'
const TEMPERATURE = 0.2

/**
 * Translate a gloss string into the other language (used for AI add flows in gloss modal)
 */
export async function translateGlosses(
  apiKey: string,
  sourceLang: string,
  targetLang: string,
  items: string[]
): Promise<string[]> {
  const started = performance.now()
  if (!items.length) return []
  const client = new OpenAI({ apiKey, dangerouslyAllowBrowser: true })

  const prompt = `Translate these expressions from ${sourceLang} to ${targetLang}. Return JSON { "translations": ["..."] } in the same order. Items:\n${items
    .map((i) => `- ${i}`)
    .join('\n')}`

  try {
    const response = await client.chat.completions.create({
      model: MODEL_NAME,
      temperature: TEMPERATURE,
      messages: [
        { role: 'system', content: 'Return JSON only.' },
        { role: 'user', content: prompt }
      ],
      response_format: {
        type: 'json_schema',
        json_schema: {
          name: 'translations',
          schema: {
            type: 'object',
            properties: {
              translations: {
                type: 'array',
                items: { type: 'string' }
              }
            },
            required: ['translations'],
            additionalProperties: false
          },
          strict: true
        }
      }
    })

    const content = response.choices[0]?.message?.content || '{}'
    const parsed = JSON.parse(content)
    const translations = (parsed.translations || []).filter(
      (t: unknown) => typeof t === 'string' && t.trim()
    )
    await logAi('translateGlosses.success', [], {
      sourceLang,
      targetLang,
      items: items.length,
      promptLength: prompt.length,
      translationsCount: translations.length,
      durationMs: Math.round(performance.now() - started)
    })
    return translations
  } catch (err) {
    await logAi('translateGlosses.error', [], {
      sourceLang,
      targetLang,
      items: items.length,
      promptLength: prompt.length,
      error: err instanceof Error ? err.message : String(err),
      durationMs: Math.round(performance.now() - started)
    })
    throw err
  }
}

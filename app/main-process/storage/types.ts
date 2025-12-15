/**
 * Shared types for main process
 */

export type GlossRef = string

export interface Gloss {
  content: string
  language: string
  slug?: string
  transcriptions: Record<string, string>
  logs: Record<string, string>
  morphologically_related: GlossRef[]
  parts: GlossRef[]
  has_similar_meaning: GlossRef[]
  sounds_similar: GlossRef[]
  usage_examples: GlossRef[]
  to_be_differentiated_from: GlossRef[]
  collocations: GlossRef[]
  typical_follow_up: GlossRef[]
  children: GlossRef[]
  translations: GlossRef[]
  notes: GlossRef[]
  tags: GlossRef[]
  needsHumanCheck: boolean
  excludeFromLearning: boolean
  decorativeImages?: string[]
  semanticImages?: string[]
  unambigiousImages?: string[]
}

export interface UsageInfo {
  usedAsPart: GlossRef[]
  usedAsUsageExample: GlossRef[]
  usedAsTranslation: GlossRef[]
}

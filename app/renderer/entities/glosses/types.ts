/**
 * Gloss type definition matching src/schema/gloss.schema.json
 */

export type GlossRef = string // Pattern: {iso_code}:{slug}

export interface Gloss {
  content: string
  language: string // ISO 639-3 code
  slug?: string // Set after loading/creating
  transcriptions: Record<string, string>
  logs: Record<string, string> // ISO timestamp keys
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
}

export interface UsageInfo {
  usedAsPart: GlossRef[]
  usedAsUsageExample: GlossRef[]
  usedAsTranslation: GlossRef[]
}

export type GoalType = 'procedural' | 'understanding'
export type GoalState = 'red' | 'yellow' | 'green'

export interface TreeNode {
  gloss: Gloss
  role: 'root' | 'part' | 'translation' | 'usage' | 'usage_part'
  marker: string
  children: TreeNode[]
  warnings: {
    nativeMissing: boolean
    targetMissing: boolean
    usageMissing: boolean
    partsMissing: boolean
  }
  bold: boolean
  goalType?: GoalType
  state?: GoalState
}

export const RELATIONSHIP_FIELDS = [
  'morphologically_related',
  'parts',
  'has_similar_meaning',
  'sounds_similar',
  'usage_examples',
  'to_be_differentiated_from',
  'collocations',
  'typical_follow_up',
  'children',
  'translations',
  'notes',
  'tags'
] as const

export const WITHIN_LANGUAGE_RELATIONS = new Set([
  'morphologically_related',
  'parts',
  'has_similar_meaning',
  'sounds_similar',
  'usage_examples',
  'to_be_differentiated_from',
  'collocations',
  'typical_follow_up'
])

export const SYMMETRICAL_RELATIONS = new Set([
  'morphologically_related',
  'has_similar_meaning',
  'sounds_similar',
  'to_be_differentiated_from',
  'translations'
])

export type RelationshipField = typeof RELATIONSHIP_FIELDS[number]

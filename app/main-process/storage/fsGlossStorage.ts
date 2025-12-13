import fs from 'fs'
import path from 'path'
import { deriveSlug } from './slug'
import {
  RELATIONSHIP_FIELDS,
  WITHIN_LANGUAGE_RELATIONS,
  SYMMETRICAL_RELATIONS,
  type RelationshipField
} from './relationRules'
import type { Gloss } from './types'

/**
 * File system-based gloss storage
 * Ported from src/shared/storage.py:GlossStorage
 */
export class GlossStorage {
  constructor(
    private dataRoot: string,
    private situationsRoot: string
  ) {}

  private languageDir(language: string): string {
    const lang = language.toLowerCase().trim()
    const dir = path.join(this.dataRoot, 'gloss', lang)
    fs.mkdirSync(dir, { recursive: true })
    return dir
  }

  private pathFor(language: string, slug: string): string {
    return path.join(this.languageDir(language), `${slug}.json`)
  }

  loadGloss(language: string, slug: string): Gloss | null {
    const filePath = this.pathFor(language, slug)
    if (!fs.existsSync(filePath)) return null

    try {
      const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'))
      return this.fromDict(data, slug, language)
    } catch (error) {
      console.error(`Failed to load gloss ${language}:${slug}:`, error)
      return null
    }
  }

  resolveReference(ref: string): Gloss | null {
    const parts = ref.split(':')
    if (parts.length < 2) return null
    const language = parts[0]?.trim()
    const slug = parts.slice(1).join(':').trim()
    if (!language || !slug) return null
    return this.loadGloss(language, slug)
  }

  findGlossByContent(language: string, content: string): Gloss | null {
    try {
      const slug = deriveSlug(content)
      return this.loadGloss(language, slug)
    } catch {
      return null
    }
  }

  ensureGloss(language: string, content: string): Gloss {
    const existing = this.findGlossByContent(language, content)
    if (existing) return existing

    const gloss: Gloss = {
      content,
      language: language.toLowerCase().trim(),
      transcriptions: {},
      logs: {},
      morphologically_related: [],
      parts: [],
      has_similar_meaning: [],
      sounds_similar: [],
      usage_examples: [],
      to_be_differentiated_from: [],
      collocations: [],
      typical_follow_up: [],
      children: [],
      translations: [],
      notes: [],
      tags: [],
      needsHumanCheck: false,
      excludeFromLearning: false
    }

    return this.createGloss(gloss)
  }

  createGloss(gloss: Gloss): Gloss {
    const slug = deriveSlug(gloss.content)
    const language = gloss.language.toLowerCase().trim()
    const filePath = this.pathFor(language, slug)

    if (fs.existsSync(filePath)) {
      // Gloss already exists, load and return it
      return this.loadGloss(language, slug)!
    }

    gloss.slug = slug
    gloss.language = language
    this.writeGloss(filePath, gloss)
    return gloss
  }

  saveGloss(gloss: Gloss): void {
    if (!gloss.slug || !gloss.language) {
      throw new Error('Gloss must have language and slug before saving.')
    }
    const filePath = this.pathFor(gloss.language, gloss.slug)
    this.writeGloss(filePath, gloss)
  }

  deleteGloss(language: string, slug: string): void {
    const filePath = this.pathFor(language, slug)
    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath)
    }
  }

  private writeGloss(filePath: string, gloss: Gloss): void {
    const data = this.toDict(gloss)
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf-8')
  }

  private fromDict(data: any, slug?: string, language?: string): Gloss {
    return {
      content: data.content ?? '',
      language: language?.toLowerCase() ?? data.language?.toLowerCase() ?? 'und',
      slug,
      transcriptions: data.transcriptions ?? {},
      logs: data.logs ?? {},
      morphologically_related: data.morphologically_related ?? [],
      parts: data.parts ?? [],
      has_similar_meaning: data.has_similar_meaning ?? [],
      sounds_similar: data.sounds_similar ?? [],
      usage_examples: data.usage_examples ?? [],
      to_be_differentiated_from: data.to_be_differentiated_from ?? [],
      collocations: data.collocations ?? [],
      typical_follow_up: data.typical_follow_up ?? [],
      children: data.children ?? [],
      translations: data.translations ?? [],
      notes: data.notes ?? [],
      tags: data.tags ?? [],
      needsHumanCheck: data.needsHumanCheck ?? false,
      excludeFromLearning: data.excludeFromLearning ?? false
    }
  }

  private toDict(gloss: Gloss): Omit<Gloss, 'slug'> {
    const { slug, ...data } = gloss
    void slug // Mark as intentionally unused
    return data
  }

  attachRelation(base: Gloss, field: RelationshipField, target: Gloss): void {
    if (!RELATIONSHIP_FIELDS.includes(field)) {
      throw new Error(`Unknown relation field: ${field}`)
    }

    if (WITHIN_LANGUAGE_RELATIONS.has(field) && target.language !== base.language) {
      throw new Error('This relationship must stay within the same language.')
    }

    const ref = `${target.language}:${target.slug}`
    const existing = (base as any)[field] ?? []

    if (!existing.includes(ref)) {
      (base as any)[field] = [...existing, ref]
      this.saveGloss(base)
    }

    // Handle symmetrical relations
    if (SYMMETRICAL_RELATIONS.has(field)) {
      const backRef = `${base.language}:${base.slug}`
      const targetRelations = (target as any)[field] ?? []
      if (!targetRelations.includes(backRef)) {
        (target as any)[field] = [...targetRelations, backRef]
        this.saveGloss(target)
      }
    }
  }

  detachRelation(base: Gloss, field: RelationshipField, targetRef: string): void {
    const baseAny = base as Record<string, any>
    const existing = baseAny[field] ?? []
    baseAny[field] = existing.filter((r: string) => r !== targetRef)
    this.saveGloss(base)

    // Handle symmetrical cleanup
    if (SYMMETRICAL_RELATIONS.has(field)) {
      const target = this.resolveReference(targetRef)
      if (target) {
        const backRef = `${base.language}:${base.slug}`
        const targetAny = target as Record<string, any>
        const targetRelations = targetAny[field] ?? []
        targetAny[field] = targetRelations.filter((r: string) => r !== backRef)
        this.saveGloss(target)
      }
    }
  }

  listGlosses(language?: string): Gloss[] {
    const glosses: Gloss[] = []

    if (language) {
      const dir = this.languageDir(language)
      if (!fs.existsSync(dir)) return glosses

      const files = fs.readdirSync(dir)
      for (const file of files) {
        if (!file.endsWith('.json')) continue
        const slug = file.replace('.json', '')
        const gloss = this.loadGloss(language, slug)
        if (gloss) glosses.push(gloss)
      }
    } else {
      // List all glosses across all languages
      const glossDir = path.join(this.dataRoot, 'gloss')
      if (!fs.existsSync(glossDir)) return glosses

      const languages = fs.readdirSync(glossDir)
      for (const lang of languages) {
        glosses.push(...this.listGlosses(lang))
      }
    }

    return glosses
  }
}

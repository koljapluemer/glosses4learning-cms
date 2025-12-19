<template>
  <ModalShell :open="open" title="Edit Gloss" size="xl" @close="$emit('close')">
    <div v-if="loading" class="py-8 flex justify-center">
      <span class="loading loading-spinner loading-lg"></span>
    </div>

    <div v-else-if="!gloss" class="alert alert-error">Gloss not found.</div>

    <div v-else class="flex flex-col gap-6">
      <fieldset class="fieldset">
        <label for="gloss-content" class="label">
          Content ({{ gloss.language.toUpperCase() }})
        </label>
        <input
          id="gloss-content"
          v-model="contentDraft"
          type="text"
          class="input input-bordered w-full"
          @blur="handleContentBlur"
        />
      </fieldset>

      <div class="flex flex-wrap gap-2">
        <button class="btn btn-outline" @click="toggleNeedsCheck">
          {{ gloss.needsHumanCheck ? 'Unset needs check' : 'Mark needs check' }}
        </button>
        <button class="btn btn-outline" @click="toggleExclude">
          {{ gloss.excludeFromLearning ? 'Include in learning' : 'Exclude from learning' }}
        </button>
      </div>

      <section class="flex flex-col gap-4">
        <fieldset class="fieldset">
          <label for="translation-input" class="label">
            Translation ({{ otherLanguage?.toUpperCase() || 'LANG' }})
          </label>
          <input
            id="translation-input"
            v-model="translationDraft"
            type="text"
            class="input input-bordered w-full"
            :placeholder="`Add translation (${otherLanguage?.toUpperCase() || 'lang'})`"
            list="translation-suggestions"
            @keyup.enter="addTranslation"
          />
          <datalist id="translation-suggestions">
            <option v-for="s in translationSuggestions" :key="s.slug" :value="s.content" />
          </datalist>
        </fieldset>
        <button class="btn self-start" :disabled="!translationDraft.trim()" @click="addTranslation">
          Add translation
        </button>
        <fieldset class="fieldset">
          <label for="translation-context" class="label">Context (optional)</label>
          <input
            id="translation-context"
            v-model="translationContext"
            type="text"
            class="input input-bordered w-full"
            placeholder="Context for AI suggestions"
          />
        </fieldset>
        <button
          class="btn self-start"
          :disabled="aiTranslating || translationBlocked"
          @click="generateTranslations"
        >
          AI add translations
        </button>
        <button
          class="btn btn-outline self-start"
          v-if="!hasTranslations"
          :disabled="translationBlocked"
          @click="markTranslationImpossible"
        >
          Mark translation impossible
        </button>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="ref in gloss.translations || []"
            :key="ref"
            class="badge badge-outline gap-2"
          >
            {{ renderRef(ref) }}
            <button class="btn btn-ghost btn-xs" @click="detach('translations', ref)">
              <X class="w-4 h-4" />
            </button>
          </span>
        </div>
      </section>

      <section class="flex flex-col gap-4">
        <fieldset class="fieldset">
          <label for="part-input" class="label">Part ({{ gloss.language.toUpperCase() }})</label>
          <input
            id="part-input"
            v-model="partDraft"
            type="text"
            class="input input-bordered w-full"
            :placeholder="`Add part (${gloss.language.toUpperCase()})`"
            list="part-suggestions"
            @keyup.enter="addPart"
          />
          <datalist id="part-suggestions">
            <option v-for="s in partSuggestions" :key="s.slug" :value="s.content" />
          </datalist>
        </fieldset>
        <button class="btn self-start" :disabled="!partDraft.trim()" @click="addPart">Add part</button>
        <fieldset class="fieldset">
          <label for="parts-context" class="label">Context (optional)</label>
          <input
            id="parts-context"
            v-model="partsContext"
            type="text"
            class="input input-bordered w-full"
            placeholder="Context for AI suggestions"
          />
        </fieldset>
        <button class="btn self-start" :disabled="aiParts || partsBlocked" @click="generateParts">
          AI add parts
        </button>
        <button
          class="btn btn-outline self-start"
          :disabled="partsBlocked || hasParts"
          @click="markUnsplittable"
        >
          Mark unsplittable
        </button>
        <div class="flex flex-wrap gap-2">
          <span v-for="ref in gloss.parts || []" :key="ref" class="badge badge-outline gap-2">
            {{ renderRef(ref) }}
            <button class="btn btn-ghost btn-xs" @click="detach('parts', ref)">
              <X class="w-4 h-4" />
            </button>
          </span>
        </div>
      </section>

      <section class="flex flex-col gap-4">
        <fieldset class="fieldset">
          <label for="usage-input" class="label">Usage example</label>
          <input
            id="usage-input"
            v-model="usageDraft"
            type="text"
            class="input input-bordered w-full"
            placeholder="Add usage example"
            list="usage-suggestions"
            @keyup.enter="addUsage"
          />
          <datalist id="usage-suggestions">
            <option v-for="s in usageSuggestions" :key="s.slug" :value="s.content" />
          </datalist>
        </fieldset>
        <button class="btn self-start" :disabled="!usageDraft.trim()" @click="addUsage">
          Add usage
        </button>
        <fieldset class="fieldset">
          <label for="usage-context" class="label">Context (optional)</label>
          <input
            id="usage-context"
            v-model="usageContext"
            type="text"
            class="input input-bordered w-full"
            placeholder="Context for AI suggestions"
          />
        </fieldset>
        <button class="btn self-start" :disabled="aiUsage || usageBlocked" @click="generateUsage">
          AI add usage
        </button>
        <button
          class="btn btn-outline self-start"
          :disabled="usageBlocked || hasUsage"
          @click="markUsageImpossible"
        >
          Mark usage impossible
        </button>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="ref in gloss.usage_examples || []"
            :key="ref"
            class="badge badge-outline gap-2"
          >
            {{ renderRef(ref) }}
            <button class="btn btn-ghost btn-xs" @click="detach('usage_examples', ref)">
              <X class="w-4 h-4" />
            </button>
          </span>
        </div>
      </section>

      <section class="flex flex-col gap-4">
        <fieldset class="fieldset">
          <label for="child-input" class="label">Child gloss</label>
          <input
            id="child-input"
            v-model="childDraft"
            type="text"
            class="input input-bordered w-full"
            placeholder="Add child gloss"
            list="child-suggestions"
            @keyup.enter="addChild"
          />
          <datalist id="child-suggestions">
            <option v-for="s in childSuggestions" :key="s.slug" :value="s.content" />
          </datalist>
        </fieldset>
        <button class="btn self-start" :disabled="!childDraft.trim()" @click="addChild">
          Add child
        </button>
        <div class="flex flex-wrap gap-2">
          <span v-for="ref in gloss.children || []" :key="ref" class="badge badge-outline gap-2">
            {{ renderRef(ref) }}
            <button class="btn btn-ghost btn-xs" @click="detach('children', ref)">
              <X class="w-4 h-4" />
            </button>
          </span>
        </div>
      </section>

      <section class="flex flex-col gap-4">
        <fieldset class="fieldset">
          <label for="note-language" class="label">Note language</label>
          <select id="note-language" v-model="noteLang" class="select select-bordered w-full">
            <option :value="nativeLanguage">Native ({{ nativeLanguage.toUpperCase() }})</option>
            <option :value="targetLanguage">Target ({{ targetLanguage.toUpperCase() }})</option>
          </select>
        </fieldset>
        <fieldset class="fieldset">
          <label for="note-input" class="label">Note</label>
          <input
            id="note-input"
            v-model="noteDraft"
            type="text"
            class="input input-bordered w-full"
            placeholder="Add note"
            @keyup.enter="addNote"
          />
        </fieldset>
        <button class="btn self-start" :disabled="!noteDraft.trim()" @click="addNote">Add note</button>
        <div class="flex flex-wrap gap-2">
          <span v-for="ref in gloss.notes || []" :key="ref" class="badge badge-outline gap-2">
            {{ renderRef(ref) }}
            <button class="btn btn-ghost btn-xs" title="Detach" @click="detach('notes', ref)">
              <X class="w-4 h-4" />
            </button>
            <button class="btn btn-ghost btn-xs text-error" title="Delete note" @click="deleteNote(ref)">
              <Trash2 class="w-4 h-4" />
            </button>
          </span>
        </div>
      </section>

      <section class="flex flex-col gap-4">
        <fieldset class="fieldset">
          <label class="label">Transcriptions</label>
          <div class="flex flex-col gap-2">
            <div
              v-for="(val, key) in transcriptions"
              :key="key"
              class="flex flex-wrap items-center gap-2"
            >
              <input v-model="transcriptionKeys[key]" class="input input-bordered w-28 md:w-32" />
              <input v-model="transcriptions[key]" class="input input-bordered flex-1 min-w-[12rem]" />
              <button class="btn btn-outline btn-xs" @click="removeTranscription(key)">
                <X class="w-4 h-4" />
              </button>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <input v-model="newTranscriptionKey" class="input input-bordered w-28 md:w-32" />
              <input v-model="newTranscriptionVal" class="input input-bordered flex-1 min-w-[12rem]" />
              <button
                class="btn"
                :disabled="!newTranscriptionKey.trim() || !newTranscriptionVal.trim()"
                @click="addTranscription"
              >
                Add transcription
              </button>
            </div>
          </div>
        </fieldset>
      </section>

      <section class="flex flex-col gap-4">
        <label class="label">Images</label>

        <div class="flex flex-col gap-2">
          <div class="text-sm font-medium">Decorative</div>
          <button class="btn btn-sm self-start" @click="pickImage('decorative')">
            Add decorative image
          </button>
          <div v-if="gloss.decorativeImages?.length" class="flex flex-wrap gap-2">
            <div
              v-for="(img, idx) in gloss.decorativeImages"
              :key="img"
              class="relative w-24 h-24 border border-base-300 rounded"
            >
              <img
                :src="imageUrl(img)"
                class="w-full h-full object-cover rounded"
                :alt="img"
              />
              <button
                class="btn btn-ghost btn-xs absolute top-0 right-0"
                @click="removeImage('decorative', idx)"
              >
                <X class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        <div class="flex flex-col gap-2">
          <div class="text-sm font-medium">Semantic</div>
          <button class="btn btn-sm self-start" @click="pickImage('semantic')">
            Add semantic image
          </button>
          <div v-if="gloss.semanticImages?.length" class="flex flex-wrap gap-2">
            <div
              v-for="(img, idx) in gloss.semanticImages"
              :key="img"
              class="relative w-24 h-24 border border-base-300 rounded"
            >
              <img
                :src="imageUrl(img)"
                class="w-full h-full object-cover rounded"
                :alt="img"
              />
              <button
                class="btn btn-ghost btn-xs absolute top-0 right-0"
                @click="removeImage('semantic', idx)"
              >
                <X class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        <div class="flex flex-col gap-2">
          <div class="text-sm font-medium">Unambiguous</div>
          <button class="btn btn-sm self-start" @click="pickImage('unambiguous')">
            Add unambiguous image
          </button>
          <div v-if="gloss.unambigiousImages?.length" class="flex flex-wrap gap-2">
            <div
              v-for="(img, idx) in gloss.unambigiousImages"
              :key="img"
              class="relative w-24 h-24 border border-base-300 rounded"
            >
              <img
                :src="imageUrl(img)"
                class="w-full h-full object-cover rounded"
                :alt="img"
              />
              <button
                class="btn btn-ghost btn-xs absolute top-0 right-0"
                @click="removeImage('unambiguous', idx)"
              >
                <X class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </section>

      <div class="flex flex-col gap-2 border-t pt-4">
        <div class="text-light">Deleting will remove this gloss and clean references.</div>
        <button class="btn btn-error self-start" @click="deleteGloss">Delete Gloss</button>
      </div>
    </div>

    <GoalConfirmModal
      :open="aiModalOpen"
      :title="aiModalTitle"
      message="Select which suggestions to attach"
      :goals="aiModalItems"
      @close="aiModalOpen = false"
      @confirm="applyAiSuggestions"
    />

    <ModalShell :open="showFilenameModal" title="Image Filename" size="sm" @close="cancelFilenameInput">
      <div class="flex flex-col gap-4">
        <fieldset class="fieldset">
          <label for="image-filename" class="label">
            Filename (alphanumeric and underscores only)
          </label>
          <input
            id="image-filename"
            v-model="filenameInput"
            type="text"
            class="input input-bordered w-full"
            placeholder="e.g. apple_fruit_red"
            @keyup.enter="confirmFilename"
          />
        </fieldset>
        <div class="flex gap-2 justify-end">
          <button class="btn btn-sm" @click="cancelFilenameInput">Cancel</button>
          <button class="btn btn-sm btn-primary" :disabled="!filenameInput.trim()" @click="confirmFilename">
            Upload
          </button>
        </div>
      </div>
    </ModalShell>
  </ModalShell>
</template>

<script setup lang="ts">
import { computed, onMounted, watch, ref, toRaw } from 'vue'
import { X, Trash2 } from 'lucide-vue-next'
import ModalShell from '../../dumb/ModalShell.vue'
import { useToasts } from '../toast-center/useToasts'
import type { Gloss } from '../../../main-process/storage/types'
import type { RelationshipField } from '../../entities/glosses/relationRules'
import {
  generateTranslations as aiTranslationsGen,
  generateParts as aiPartsGen,
  generateUsage as aiUsageGen
} from '../ai-batch-tools/useAiGeneration'
import { useSettings } from '../../entities/system/settingsStore'
import GoalConfirmModal from '../goal-confirm-modal/GoalConfirmModal.vue'
import { paraphraseDisplay } from '../../entities/glosses/goalState'

const props = defineProps<{
  open: boolean
  glossRef: string | null
  nativeLanguage: string
  targetLanguage: string
}>()

const emit = defineEmits<{
  close: []
  saved: []
  deleted: [ref?: string]
}>()

const { success, error, info } = useToasts()
const { settings } = useSettings()

const loading = ref(false)
const gloss = ref<Gloss | null>(null)
const contentDraft = ref('')
const translationDraft = ref('')
const translationSuggestions = ref<Gloss[]>([])
const partDraft = ref('')
const partSuggestions = ref<Gloss[]>([])
const usageDraft = ref('')
const usageSuggestions = ref<Gloss[]>([])
const childDraft = ref('')
const childSuggestions = ref<Gloss[]>([])
const noteDraft = ref('')
const noteLang = ref(props.nativeLanguage)
const translationContext = ref('')
const partsContext = ref('')
const usageContext = ref('')
const aiModalOpen = ref(false)
const aiModalTitle = ref('')
const aiModalItems = ref<string[]>([])
const aiModalKind = ref<'translations' | 'parts' | 'usage' | null>(null)

const transcriptions = ref<Record<string, string>>({})
const transcriptionKeys = ref<Record<string, string>>({})
const newTranscriptionKey = ref('')
const newTranscriptionVal = ref('')
const displayCache = ref(new Map<string, string>())
const imageCache = ref<Map<string, string>>(new Map())

type ImageCategory = 'decorative' | 'semantic' | 'unambiguous'

const showFilenameModal = ref(false)
const filenameInput = ref('')
const pendingImageData = ref<{ base64: string; category: ImageCategory } | null>(null)

const hasTranslations = computed(() => (gloss.value?.translations?.length || 0) > 0)
const hasParts = computed(() => (gloss.value?.parts?.length || 0) > 0)
const hasUsage = computed(() => (gloss.value?.usage_examples?.length || 0) > 0)
const aiTranslating = ref(false)
const aiParts = ref(false)
const aiUsage = ref(false)

function logHas(marker: string): boolean {
  const logs = gloss.value?.logs
  if (!logs || typeof logs !== 'object') return false
  return Object.values(logs).some((v) => String(v).includes(marker))
}

const translationBlocked = computed(() => {
  if (!gloss.value) return false
  const other =
    gloss.value.language === props.nativeLanguage ? props.targetLanguage : props.nativeLanguage
  return logHas(`TRANSLATION_CONSIDERED_IMPOSSIBLE:${other}`)
})

const partsBlocked = computed(() => logHas('SPLIT_CONSIDERED_UNNECESSARY'))

const usageBlocked = computed(() =>
  gloss.value ? logHas(`USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE:${gloss.value.language}`) : false
)

const otherLanguage = computed(() => {
  if (!gloss.value) return null
  if (gloss.value.language === props.nativeLanguage) return props.targetLanguage
  if (gloss.value.language === props.targetLanguage) return props.nativeLanguage
  return null
})

function renderRef(refStr: string): string {
  const cached = displayCache.value.get(refStr)
  if (cached) return cached
  return refStr
}

async function loadGloss() {
  if (!props.glossRef) {
    gloss.value = null
    return
  }

  loading.value = true
  try {
    const data = await window.electronAPI.gloss.resolveRef(props.glossRef)
    gloss.value = data
    contentDraft.value = data?.content || ''
    transcriptions.value = { ...(data?.transcriptions || {}) }
    transcriptionKeys.value = Object.fromEntries(
      Object.keys(transcriptions.value).map((k) => [k, k])
    )
    await hydrateDisplayCache(data)
  } catch (err) {
    console.error(err)
    error('Failed to load gloss')
  } finally {
    loading.value = false
  }
}

async function hydrateDisplayCache(current: Gloss) {
  const refs = new Set<string>([
    ...(current.translations || []),
    ...(current.parts || []),
    ...(current.usage_examples || []),
    ...(current.children || []),
    ...(current.notes || [])
  ])

  // Always include self
  refs.add(`${current.language}:${current.slug}`)

  for (const ref of refs) {
    if (displayCache.value.has(ref)) continue
    const g = await window.electronAPI.gloss.resolveRef(ref)
    if (g) {
      displayCache.value.set(ref, paraphraseDisplay(g))
    }
  }
}

async function handleContentBlur() {
  if (!gloss.value) return
  const newContent = contentDraft.value.trim()
  if (!newContent || newContent === gloss.value.content) return

  try {
    const usage = await window.electronAPI.gloss.checkReferences(
      `${gloss.value.language}:${gloss.value.slug}`
    )
    const hasRefs =
      (usage.usedAsPart?.length || 0) > 0 ||
      (usage.usedAsUsageExample?.length || 0) > 0 ||
      (usage.usedAsTranslation?.length || 0) > 0

    if (hasRefs) {
      const lines = [
        `Change will affect references:`,
        `Parts: ${usage.usedAsPart.join(', ') || 'none'}`,
        `Usages: ${usage.usedAsUsageExample.join(', ') || 'none'}`,
        `Translations: ${usage.usedAsTranslation.join(', ') || 'none'}`,
        'Proceed?'
      ]
      const ok = confirm(lines.join('\n'))
      if (!ok) {
        contentDraft.value = gloss.value.content
        return
      }
    }

    await window.electronAPI.gloss.updateContent(
      `${gloss.value.language}:${gloss.value.slug}`,
      newContent
    )
    success('Content updated')
    await loadGloss()
    emit('saved')
  } catch (err) {
    console.error(err)
    error('Failed to update content')
  }
}

async function detach(field: RelationshipField, targetRef: string) {
  if (!gloss.value) return
  try {
    await window.electronAPI.gloss.detachRelation(
      `${gloss.value.language}:${gloss.value.slug}`,
      field,
      targetRef
    )
    success('Detached')
    await loadGloss()
    emit('saved')
  } catch (err) {
    console.error(err)
    error('Failed to detach')
  }
}

async function addTranslation() {
  if (!gloss.value || !otherLanguage.value) return
  const content = translationDraft.value.trim()
  if (!content) return

  try {
    const newGloss = await window.electronAPI.gloss.ensure(otherLanguage.value, content)
    const baseRef = `${gloss.value.language}:${gloss.value.slug}`
    const targetRef = `${newGloss.language}:${newGloss.slug}`
    await window.electronAPI.gloss.attachRelation(baseRef, 'translations', targetRef)
    success('Translation added')
    translationDraft.value = ''
    await loadGloss()
    emit('saved')
  } catch (err) {
    console.error(err)
    error('Failed to add translation')
  }
}

async function addPart() {
  if (!gloss.value) return
  const content = partDraft.value.trim()
  if (!content) return

  try {
    const newGloss = await window.electronAPI.gloss.ensure(gloss.value.language, content)
    const baseRef = `${gloss.value.language}:${gloss.value.slug}`
    const targetRef = `${newGloss.language}:${newGloss.slug}`
    await window.electronAPI.gloss.attachRelation(baseRef, 'parts', targetRef)
    success('Part added')
    partDraft.value = ''
    await loadGloss()
    emit('saved')
  } catch (err) {
    console.error(err)
    error('Failed to add part')
  }
}

async function addUsage() {
  if (!gloss.value) return
  const content = usageDraft.value.trim()
  if (!content) return

  try {
    const newGloss = await window.electronAPI.gloss.ensure(gloss.value.language, content)
    const baseRef = `${gloss.value.language}:${gloss.value.slug}`
    const targetRef = `${newGloss.language}:${newGloss.slug}`
    await window.electronAPI.gloss.attachRelation(baseRef, 'usage_examples', targetRef)
    success('Usage added')
    usageDraft.value = ''
    await loadGloss()
    emit('saved')
  } catch (err) {
    console.error(err)
    error('Failed to add usage example')
  }
}

async function generateTranslations() {
  if (!gloss.value || !otherLanguage.value) return
  const apiKey = settings.value.openaiApiKey
  if (!apiKey) {
    error('Set OpenAI API key in settings')
    return
  }
  aiTranslating.value = true
  try {
    const res = await aiTranslationsGen(
      apiKey,
      gloss.value.language === props.nativeLanguage ? 'toTarget' : 'toNative',
      [`${gloss.value.language}:${gloss.value.slug}`],
      props.nativeLanguage,
      props.targetLanguage,
      { context: translationContext.value }
    )
    aiModalKind.value = 'translations'
    aiModalItems.value = res[0]?.suggestions || []
    aiModalTitle.value = 'Confirm translations'
    aiModalOpen.value = true
  } catch (err) {
    console.error(err)
    error('AI translation failed')
  } finally {
    aiTranslating.value = false
  }
}

async function generateParts() {
  if (!gloss.value) return
  const apiKey = settings.value.openaiApiKey
  if (!apiKey) {
    error('Set OpenAI API key in settings')
    return
  }
  aiParts.value = true
  try {
    const res = await aiPartsGen(apiKey, [`${gloss.value.language}:${gloss.value.slug}`], {
      context: partsContext.value
    })
    aiModalKind.value = 'parts'
    aiModalItems.value = res[0]?.suggestions || []
    aiModalTitle.value = 'Confirm parts'
    aiModalOpen.value = true
  } catch (err) {
    console.error(err)
    error('AI parts failed')
  } finally {
    aiParts.value = false
  }
}

async function generateUsage() {
  if (!gloss.value) return
  const apiKey = settings.value.openaiApiKey
  if (!apiKey) {
    error('Set OpenAI API key in settings')
    return
  }
  aiUsage.value = true
  try {
    const res = await aiUsageGen(apiKey, [`${gloss.value.language}:${gloss.value.slug}`], {
      context: usageContext.value
    })
    aiModalKind.value = 'usage'
    aiModalItems.value = res[0]?.suggestions || []
    aiModalTitle.value = 'Confirm usage examples'
    aiModalOpen.value = true
  } catch (err) {
    console.error(err)
    error('AI usage failed')
  } finally {
    aiUsage.value = false
  }
}

async function applyAiSuggestions(selected: string[]) {
  if (!gloss.value || !aiModalKind.value) return
  aiModalOpen.value = false

  // Check if all were rejected (user selected nothing but there were suggestions)
  const allRejected = selected.length === 0 && aiModalItems.value.length > 0

  if (allRejected) {
    // Set appropriate flag based on kind
    if (aiModalKind.value === 'translations' && otherLanguage.value) {
      const marker = `TRANSLATION_CONSIDERED_IMPOSSIBLE:${otherLanguage.value}`
      await window.electronAPI.gloss.markLog(`${gloss.value.language}:${gloss.value.slug}`, marker)
      success('Marked as untranslatable')
    } else if (aiModalKind.value === 'parts') {
      const marker = 'SPLIT_CONSIDERED_UNNECESSARY'
      await window.electronAPI.gloss.markLog(`${gloss.value.language}:${gloss.value.slug}`, marker)
      success('Marked unsplittable')
    } else if (aiModalKind.value === 'usage') {
      const marker = `USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE:${gloss.value.language}`
      await window.electronAPI.gloss.markLog(`${gloss.value.language}:${gloss.value.slug}`, marker)
      success('Marked usage impossible')
    }
    await loadGloss()
    emit('saved')
    return
  }

  if (!selected.length) return

  if (aiModalKind.value === 'translations' && otherLanguage.value) {
    for (const text of selected) {
      translationDraft.value = text
      await addTranslation()
    }
  } else if (aiModalKind.value === 'parts') {
    for (const text of selected) {
      partDraft.value = text
      await addPart()
    }
  } else if (aiModalKind.value === 'usage') {
    for (const text of selected) {
      usageDraft.value = text
      await addUsage()
    }
  }
}

async function addChild() {
  if (!gloss.value) return
  const content = childDraft.value.trim()
  if (!content) return
  try {
    const newGloss = await window.electronAPI.gloss.ensure(gloss.value.language, content)
    const baseRef = `${gloss.value.language}:${gloss.value.slug}`
    const targetRef = `${newGloss.language}:${newGloss.slug}`
    await window.electronAPI.gloss.attachRelation(baseRef, 'children', targetRef)
    success('Child added')
    childDraft.value = ''
    await loadGloss()
    emit('saved')
  } catch (err) {
    console.error(err)
    error('Failed to add child')
  }
}

async function addNote() {
  if (!gloss.value) return
  const content = noteDraft.value.trim()
  if (!content) return

  try {
    const noteGloss = await window.electronAPI.gloss.ensure(noteLang.value, content)
    const baseRef = `${gloss.value.language}:${gloss.value.slug}`
    const targetRef = `${noteGloss.language}:${noteGloss.slug}`
    await window.electronAPI.gloss.attachRelation(baseRef, 'notes', targetRef)
    success('Note added')
    noteDraft.value = ''
    await loadGloss()
    emit('saved')
  } catch (err) {
    console.error(err)
    error('Failed to add note')
  }
}

async function deleteNote(noteRef: string) {
  if (!gloss.value) return
  try {
    const usage = await window.electronAPI.gloss.noteUsageCount(noteRef)
    if (usage.count > 1) {
      await detach('notes', noteRef)
      info(`Note used elsewhere; detached only (still referenced by ${usage.count - 1} other glosses)`)
      return
    }
    const [lang, ...slugParts] = noteRef.split(':')
    const slug = slugParts.join(':')
    const ok = confirm(`Delete note ${noteRef}? This will clean references.`)
    if (!ok) return
    await window.electronAPI.gloss.deleteWithCleanup(lang, slug)
    success('Note deleted')
    await loadGloss()
    emit('saved')
  } catch (err) {
    console.error(err)
    error('Failed to delete note')
  }
}

function removeTranscription(key: string) {
  delete transcriptions.value[key]
  delete transcriptionKeys.value[key]
  persistTranscriptions()
}

function addTranscription() {
  const k = newTranscriptionKey.value.trim()
  const v = newTranscriptionVal.value.trim()
  if (!k || !v) return
  transcriptions.value[k] = v
  transcriptionKeys.value[k] = k
  newTranscriptionKey.value = ''
  newTranscriptionVal.value = ''
  persistTranscriptions()
}

function persistTranscriptions() {
  if (!gloss.value) return
  gloss.value.transcriptions = { ...transcriptions.value }
  window.electronAPI.gloss.save(gloss.value).then(() => emit('saved'))
}

async function toggleExclude() {
  if (!gloss.value) return
  try {
    gloss.value.excludeFromLearning = !gloss.value.excludeFromLearning
    await window.electronAPI.gloss.save(gloss.value)
    emit('saved')
  } catch (err) {
    console.error(err)
    error('Failed to toggle flag')
  }
}

async function toggleNeedsCheck() {
  if (!gloss.value) return
  try {
    gloss.value.needsHumanCheck = !gloss.value.needsHumanCheck
    await window.electronAPI.gloss.save(gloss.value)
    emit('saved')
  } catch (err) {
    console.error(err)
    error('Failed to toggle flag')
  }
}

async function markTranslationImpossible() {
  if (!gloss.value || translationBlocked.value) return
  const other =
    gloss.value.language === props.nativeLanguage ? props.targetLanguage : props.nativeLanguage
  const marker = `TRANSLATION_CONSIDERED_IMPOSSIBLE:${other}`
  await window.electronAPI.gloss.markLog(`${gloss.value.language}:${gloss.value.slug}`, marker)
  success('Marked as untranslatable')
  await loadGloss()
  emit('saved')
}

async function markUnsplittable() {
  if (!gloss.value || partsBlocked.value) return
  const marker = 'SPLIT_CONSIDERED_UNNECESSARY'
  await window.electronAPI.gloss.markLog(`${gloss.value.language}:${gloss.value.slug}`, marker)
  success('Marked unsplittable')
  await loadGloss()
  emit('saved')
}

async function markUsageImpossible() {
  if (!gloss.value || usageBlocked.value) return
  const marker = `USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE:${gloss.value.language}`
  await window.electronAPI.gloss.markLog(`${gloss.value.language}:${gloss.value.slug}`, marker)
  success('Marked usage impossible')
  await loadGloss()
  emit('saved')
}

async function deleteGloss() {
  if (!gloss.value) return
  const ref = `${gloss.value.language}:${gloss.value.slug}`
  const usage = await window.electronAPI.gloss.checkReferences(ref)
  const lines = [
    `Delete ${ref}? This will clean references.`,
    `Used as part in: ${usage.usedAsPart.join(', ') || 'none'}`,
    `Used as usage example in: ${usage.usedAsUsageExample.join(', ') || 'none'}`,
    `Used as translation in: ${usage.usedAsTranslation.join(', ') || 'none'}`
  ]
  const ok = confirm(lines.join('\n'))
  if (!ok) return
  try {
    await window.electronAPI.gloss.deleteWithCleanup(gloss.value.language, gloss.value.slug!)
    success('Deleted')
    emit('deleted', ref)
  } catch (err) {
    console.error(err)
    error('Delete failed')
  }
}

async function fetchSuggestions(
  language: string,
  query: string,
  setter: (items: Gloss[]) => void
) {
  if (!language) return
  if (!query.trim()) {
    setter([])
    return
  }
  try {
    const res = await window.electronAPI.gloss.searchByContent(language, query.trim(), 10)
    setter(res)
  } catch (err) {
    console.error(err)
  }
}

function imageUrl(filename: string): string {
  const cached = imageCache.value.get(filename)
  if (cached) return cached

  window.electronAPI.image.load(filename).then((base64) => {
    imageCache.value.set(filename, `data:image/webp;base64,${base64}`)
  }).catch((err) => {
    console.error('Failed to load image', filename, err)
  })

  return ''
}

async function pickImage(category: ImageCategory) {
  if (!gloss.value) return

  try {
    const result = await window.electronAPI.image.pickFile()
    if (!result) return

    pendingImageData.value = { base64: result, category }
    filenameInput.value = ''
    showFilenameModal.value = true
  } catch (err) {
    console.error(err)
    error('Failed to open file picker')
  }
}

async function confirmFilename() {
  if (!gloss.value || !pendingImageData.value) return
  if (!filenameInput.value.trim()) return

  try {
    const { base64, category } = pendingImageData.value
    const filename = await window.electronAPI.image.upload(base64, filenameInput.value)

    const fieldMap = {
      decorative: 'decorativeImages',
      semantic: 'semanticImages',
      unambiguous: 'unambigiousImages'
    }
    const field = fieldMap[category] as 'decorativeImages' | 'semanticImages' | 'unambigiousImages'

    if (!gloss.value[field]) {
      gloss.value[field] = []
    }
    gloss.value[field]!.push(filename)

    await window.electronAPI.gloss.save(toRaw(gloss.value))
    success('Image added')
    emit('saved')

    showFilenameModal.value = false
    pendingImageData.value = null
    filenameInput.value = ''
  } catch (err) {
    console.error(err)
    error(err instanceof Error ? err.message : 'Failed to upload image')
  }
}

function cancelFilenameInput() {
  showFilenameModal.value = false
  pendingImageData.value = null
  filenameInput.value = ''
}

async function removeImage(category: ImageCategory, index: number) {
  if (!gloss.value) return

  const fieldMap = {
    decorative: 'decorativeImages',
    semantic: 'semanticImages',
    unambiguous: 'unambigiousImages'
  }
  const field = fieldMap[category] as 'decorativeImages' | 'semanticImages' | 'unambigiousImages'
  const images = gloss.value[field]

  if (!images || !images[index]) return

  const filename = images[index]
  const ok = confirm(`Remove image ${filename}?`)
  if (!ok) return

  try {
    images.splice(index, 1)
    await window.electronAPI.gloss.save(toRaw(gloss.value))

    success('Image removed')
    emit('saved')
  } catch (err) {
    console.error(err)
    error('Failed to remove image')
  }
}

watch(
  () => translationDraft.value,
  (q) => {
    if (otherLanguage.value) {
      fetchSuggestions(otherLanguage.value, q, (items) => (translationSuggestions.value = items))
    }
  }
)

watch(
  () => partDraft.value,
  (q) => fetchSuggestions(gloss.value?.language || '', q, (items) => (partSuggestions.value = items))
)

watch(
  () => usageDraft.value,
  (q) => fetchSuggestions(gloss.value?.language || '', q, (items) => (usageSuggestions.value = items))
)

watch(
  () => childDraft.value,
  (q) => fetchSuggestions(gloss.value?.language || '', q, (items) => (childSuggestions.value = items))
)

watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      await loadGloss()
    } else {
      translationDraft.value = ''
      partDraft.value = ''
      usageDraft.value = ''
      childDraft.value = ''
      noteDraft.value = ''
      translationContext.value = ''
      partsContext.value = ''
      usageContext.value = ''
    }
  }
)

onMounted(() => {
  if (props.open) {
    loadGloss()
  }
})
</script>

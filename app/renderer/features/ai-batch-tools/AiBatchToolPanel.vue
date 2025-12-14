<template>
  <div class="card bg-base-200 shadow">
    <div class="card-body space-y-3">
      <h3 class="card-title text-base">AI Tools</h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-2">
        <button class="btn btn-sm" :disabled="busy || !hasMissingTranslations" @click="runTranslations">
          Add missing translations
          <span class="badge badge-outline ml-2">{{ translationsCount }}</span>
        </button>
        <button class="btn btn-sm" :disabled="busy || !hasMissingParts" @click="runParts">
          Add missing parts
          <span class="badge badge-outline ml-2">{{ partsCount }}</span>
        </button>
        <button class="btn btn-sm" :disabled="busy || !hasMissingUsage" @click="runUsage">
          Add missing usage examples
          <span class="badge badge-outline ml-2">{{ usageCount }}</span>
        </button>
      </div>

      <div v-if="busy" class="text-sm text-base-content/70">Running AI...</div>

      <dialog :open="showModal" class="modal">
        <div class="modal-box max-w-2xl">
          <h3 class="font-semibold text-lg mb-3">{{ modalTitle }}</h3>
          <p class="text-sm text-base-content/70 mb-3">{{ modalSubtitle }}</p>
          <div class="space-y-3 max-h-96 overflow-y-auto">
            <div
              v-for="(item, idx) in proposalList"
              :key="idx"
              class="border border-base-300 rounded-lg p-3 space-y-2"
            >
              <div class="font-semibold">{{ item.glossRef }}</div>
              <div class="space-y-1">
                <label
                  v-for="(text, i) in item.suggestions"
                  :key="i"
                  class="flex items-start gap-2"
                >
                  <input
                    type="checkbox"
                    class="checkbox checkbox-sm mt-1"
                    v-model="item.selected[i]"
                  />
                  <span class="flex-1">{{ text }}</span>
                </label>
              </div>
            </div>
          </div>
          <div class="modal-action">
            <button class="btn btn-ghost" @click="closeModal">Cancel</button>
            <button class="btn btn-primary" :disabled="busy" @click="applySelected">
              Apply
            </button>
          </div>
        </div>
        <form method="dialog" class="modal-backdrop" @submit="closeModal">
          <button>close</button>
        </form>
      </dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useSettings } from '../../entities/system/settingsStore'
import { useToasts } from '../toast-center/useToasts'
import { generateTranslations, generateParts, generateUsage } from './useAiGeneration'
import type { Gloss } from '../../../main-process/storage/types'

const props = defineProps<{
  goalRef: string
  goalKind: 'procedural' | 'understanding' | null
  nativeLanguage: string
  targetLanguage: string
  missingNativeRefs: string[]
  missingTargetRefs: string[]
  missingPartsRefs: string[]
  missingUsageRefs: string[]
}>()

const emit = defineEmits<{
  applied: []
}>()

const { settings } = useSettings()
const { success, error } = useToasts()

const busy = ref(false)
const showModal = ref(false)
const modalTitle = ref('')
const modalSubtitle = ref('')

type Proposal = { glossRef: string; suggestions: string[]; selected: boolean[]; kind: 'translation' | 'parts' | 'usage'; direction?: 'toNative' | 'toTarget' }
const proposalList = reactive<Proposal[]>([])

const translationsCount = computed(
  () => props.missingNativeRefs.length + props.missingTargetRefs.length
)
const partsCount = computed(() => props.missingPartsRefs.length)
const usageCount = computed(() => props.missingUsageRefs.length)

const hasMissingTranslations = computed(() => translationsCount.value > 0)
const hasMissingParts = computed(() => partsCount.value > 0)
const hasMissingUsage = computed(() => usageCount.value > 0)

function resetModal() {
  proposalList.splice(0, proposalList.length)
}

function openModal(title: string, subtitle: string, proposals: Proposal[]) {
  modalTitle.value = title
  modalSubtitle.value = subtitle
  resetModal()
  proposals.forEach((p) => proposalList.push(p))
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function loadGlosses(refs: string[]): Promise<Gloss[]> {
  const items: Gloss[] = []
  for (const ref of refs) {
    const g = await window.electronAPI.gloss.resolveRef(ref)
    if (g) items.push(g)
  }
  return items
}

async function runTranslations() {
  const apiKey = settings.value.openaiApiKey
  if (!apiKey) {
    error('Set OpenAI API key in settings')
    return
  }
  busy.value = true
  try {
    const glossesNativeMissing = await loadGlosses(props.missingNativeRefs)
    const glossesTargetMissing = await loadGlosses(props.missingTargetRefs)

    const paraphrasedNative = glossesTargetMissing.filter((g) =>
      (g.tags || []).includes('eng:paraphrase')
    )
    const plainNative = glossesTargetMissing.filter(
      (g) => !(g.tags || []).includes('eng:paraphrase')
    )

    const toNative = await generateTranslations(
      apiKey,
      'toNative',
      glossesNativeMissing.map((g) => `${g.language}:${g.slug}`),
      props.nativeLanguage,
      props.targetLanguage
    )

    const toTargetPlain = await generateTranslations(
      apiKey,
      'toTarget',
      plainNative.map((g) => `${g.language}:${g.slug}`),
      props.nativeLanguage,
      props.targetLanguage
    )

    const toTargetParaphrase = await generateTranslations(
      apiKey,
      'paraphraseToTarget',
      paraphrasedNative.map((g) => `${g.language}:${g.slug}`),
      props.nativeLanguage,
      props.targetLanguage
    )
    const proposals: Proposal[] = []
    for (const item of toNative) {
      proposals.push({
        glossRef: item.glossRef,
        suggestions: item.suggestions,
        selected: item.suggestions.map(() => true),
        kind: 'translation',
        direction: 'toNative'
      })
    }
    for (const item of toTargetPlain) {
      proposals.push({
        glossRef: item.glossRef,
        suggestions: item.suggestions,
        selected: item.suggestions.map(() => true),
        kind: 'translation',
        direction: 'toTarget'
      })
    }
    for (const item of toTargetParaphrase) {
      proposals.push({
        glossRef: item.glossRef,
        suggestions: item.suggestions,
        selected: item.suggestions.map(() => true),
        kind: 'translation',
        direction: 'toTarget'
      })
    }
    if (!proposals.length) {
      success('No translation suggestions')
      return
    }
    openModal('Confirm translations', 'Approve translations to attach', proposals)
  } catch (err) {
    console.error(err)
    error('Translation generation failed')
  } finally {
    busy.value = false
  }
}

async function runParts() {
  const apiKey = settings.value.openaiApiKey
  if (!apiKey) {
    error('Set OpenAI API key in settings')
    return
  }
  busy.value = true
  try {
    const res = await generateParts(apiKey, props.missingPartsRefs)
    const proposals: Proposal[] = res.map((item) => ({
      glossRef: item.glossRef,
      suggestions: item.suggestions,
      selected: item.suggestions.map(() => true),
      kind: 'parts'
    }))
    if (!proposals.length) {
      success('No parts to add')
      return
    }
    openModal('Confirm parts', 'Approve parts to attach', proposals)
  } catch (err) {
    console.error(err)
    error('Parts generation failed')
  } finally {
    busy.value = false
  }
}

async function runUsage() {
  const apiKey = settings.value.openaiApiKey
  if (!apiKey) {
    error('Set OpenAI API key in settings')
    return
  }
  busy.value = true
  try {
    const res = await generateUsage(apiKey, props.missingUsageRefs)
    const proposals: Proposal[] = res.map((item) => ({
      glossRef: item.glossRef,
      suggestions: item.suggestions,
      selected: item.suggestions.map(() => true),
      kind: 'usage'
    }))
    if (!proposals.length) {
      success('No usage examples to add')
      return
    }
    openModal('Confirm usage examples', 'Approve usages to attach', proposals)
  } catch (err) {
    console.error(err)
    error('Usage generation failed')
  } finally {
    busy.value = false
  }
}

async function applySelected() {
  busy.value = true
  try {
    for (const item of proposalList) {
      const selectedTexts = item.suggestions.filter((_, idx) => item.selected[idx])
      if (!selectedTexts.length) continue
      const baseRef = item.glossRef

      if (item.kind === 'translation') {
        const targetLang =
          item.direction === 'toNative' ? props.nativeLanguage : props.targetLanguage
        for (const text of selectedTexts) {
          const newGloss = await window.electronAPI.gloss.ensure(targetLang, text)
          await window.electronAPI.gloss.attachRelation(baseRef, 'translations', `${newGloss.language}:${newGloss.slug}`)
        }
      } else if (item.kind === 'parts') {
        for (const text of selectedTexts) {
          const lang = baseRef.split(':')[0]
          const newGloss = await window.electronAPI.gloss.ensure(lang, text)
          await window.electronAPI.gloss.attachRelation(baseRef, 'parts', `${newGloss.language}:${newGloss.slug}`)
        }
      } else if (item.kind === 'usage') {
        const lang = baseRef.split(':')[0]
        for (const text of selectedTexts) {
          const usageGloss = await window.electronAPI.gloss.ensure(lang, text)
          await window.electronAPI.gloss.attachRelation(baseRef, 'usage_examples', `${usageGloss.language}:${usageGloss.slug}`)
        }
      }
    }
    success('Applied AI suggestions')
    closeModal()
    emit('applied')
  } catch (err) {
    console.error(err)
    error('Failed to apply suggestions')
  } finally {
    busy.value = false
  }
}
</script>

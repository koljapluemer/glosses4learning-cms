<template>
  <ModalShell :open="open" title="Select Situation & Languages" size="lg" @close="$emit('close')">
    <div class="space-y-4">
      <!-- Language Selection -->
      <div class="grid grid-cols-2 gap-4 pb-4 border-b">
        <fieldset class="fieldset">
          <label class="label">Native Language</label>
          <select v-model="localNative" class="select select-bordered w-full">
            <option :value="null">-- Select --</option>
            <option v-for="lang in languages" :key="lang.isoCode" :value="lang.isoCode">
              {{ lang.symbol }} {{ lang.displayName }}
            </option>
          </select>
        </fieldset>

        <fieldset class="fieldset">
          <label class="label">Target Language</label>
          <select v-model="localTarget" class="select select-bordered w-full">
            <option :value="null">-- Select --</option>
            <option v-for="lang in languages" :key="lang.isoCode" :value="lang.isoCode">
              {{ lang.symbol }} {{ lang.displayName }}
            </option>
          </select>
        </fieldset>
      </div>

      <!-- Warning if languages not set -->
      <div v-if="!localNative || !localTarget" class="alert alert-warning">
        <span>Select both languages before choosing a situation</span>
      </div>

      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search situations..."
        class="input input-bordered w-full"
        autofocus
      />

      <div v-if="loading" class="flex justify-center py-8">
        <span class="loading loading-spinner loading-lg"></span>
      </div>

      <div v-else-if="groupedSituations.length === 0" class="text-center py-8 text-base-content/60">
        No situations found. Create one to get started.
      </div>

      <div v-else class="space-y-4 max-h-96 overflow-y-auto">
        <div v-for="group in groupedSituations" :key="group.language" class="space-y-2">
          <h4 class="font-semibold text-sm uppercase tracking-wide text-base-content/70">
            {{ group.languageName }}
          </h4>
          <div class="space-y-1">
            <div
              v-for="situation in group.situations"
              :key="situation.slug"
              class="flex items-center gap-2 px-3 py-2 rounded hover:bg-base-200 transition-colors"
            >
              <button
                class="flex-1 text-left"
                :disabled="!localNative || !localTarget"
                @click="selectSituation(situation)"
              >
                {{ situation.content }}
              </button>

              <!-- Action buttons -->
              <button
                class="btn btn-ghost btn-xs"
                title="Remove situation tag"
                @click="removeSituationTag(situation)"
              >
                <X class="w-4 h-4" />
              </button>
              <button
                class="btn btn-ghost btn-xs text-error"
                title="Delete situation"
                @click="deleteSituation(situation)"
              >
                <Trash2 class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="flex gap-2 pt-4 border-t">
        <InlineAddField
          v-if="showCreateField"
          placeholder="Enter situation description..."
          autofocus
          @submit="createSituation"
          @cancel="showCreateField = false"
        />
        <button v-else class="btn btn-primary btn-sm" @click="showCreateField = true">
          <Plus class="w-4 h-4" />
          New Situation
        </button>
      </div>
    </div>
  </ModalShell>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Plus, Trash2, X } from 'lucide-vue-next'
import ModalShell from '../../dumb/ModalShell.vue'
import InlineAddField from '../../dumb/InlineAddField.vue'
import { useToasts } from '../toast-center/useToasts'
import { loadLanguages, type Language } from '../../entities/languages/loader'
import { useSettings } from '../../entities/system/settingsStore'

interface Situation {
  slug: string
  content: string
  language: string
  tags: string[]
}

interface LanguageGroup {
  language: string
  languageName: string
  situations: Situation[]
}

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  close: []
  select: [situation: Situation]
}>()

const { success, error } = useToasts()
const { settings, setNativeLanguage, setTargetLanguage, setLastSituation } = useSettings()

const searchQuery = ref('')
const situations = ref<Situation[]>([])
const loading = ref(false)
const showCreateField = ref(false)
const languages = ref<Language[]>([])
const localNative = ref<string | null>(null)
const localTarget = ref<string | null>(null)

// Language names mapping (can be extended)
const languageNames: Record<string, string> = {
  eng: 'English',
  deu: 'German',
  fra: 'French',
  spa: 'Spanish'
}

const groupedSituations = computed(() => {
  const filtered = searchQuery.value
    ? situations.value.filter((s) =>
        s.content.toLowerCase().includes(searchQuery.value.toLowerCase())
      )
    : situations.value

  const groups = new Map<string, Situation[]>()
  for (const situation of filtered) {
    const lang = situation.language
    if (!groups.has(lang)) {
      groups.set(lang, [])
    }
    groups.get(lang)!.push(situation)
  }

  const result: LanguageGroup[] = []
  for (const [language, items] of groups) {
    result.push({
      language,
      languageName: languageNames[language] || language.toUpperCase(),
      situations: items
    })
  }

  return result.sort((a, b) => a.languageName.localeCompare(b.languageName))
})

async function loadSituations() {
  loading.value = true
  try {
    situations.value = await window.electronAPI.situation.list(searchQuery.value)
  } catch (err) {
    error('Failed to load situations')
    console.error(err)
  } finally {
    loading.value = false
  }
}

async function createSituation(content: string) {
  try {
    const newSituation = await window.electronAPI.situation.create(content)
    situations.value.unshift(newSituation)
    showCreateField.value = false
    success('Situation created')
  } catch (err) {
    error('Failed to create situation')
    console.error(err)
  }
}

async function selectSituation(situation: Situation) {
  if (!localNative.value || !localTarget.value) {
    return
  }

  const ref = `${situation.language}:${situation.slug}`
  await setLastSituation(ref)
  emit('select', situation)
}

async function removeSituationTag(situation: Situation) {
  try {
    const ref = `${situation.language}:${situation.slug}`
    const gloss = await window.electronAPI.gloss.resolveRef(ref)

    gloss.tags = gloss.tags.filter((t) => t !== 'eng:situation')
    await window.electronAPI.gloss.save(gloss)

    situations.value = situations.value.filter((s) => s.slug !== situation.slug)
    success('Removed situation tag')
  } catch (err) {
    error('Failed to remove tag')
    console.error(err)
  }
}

async function deleteSituation(situation: Situation) {
  if (!confirm(`Delete "${situation.content}"? This will clean up all references.`)) {
    return
  }

  try {
    const result = await window.electronAPI.gloss.deleteWithCleanup(
      situation.language,
      situation.slug
    )
    if (result.success) {
      situations.value = situations.value.filter((s) => s.slug !== situation.slug)
      success(result.message)
    } else {
      error(result.message || 'Delete failed')
    }
  } catch (err) {
    error('Failed to delete situation')
    console.error(err)
  }
}

// Sync language changes with settings
watch(localNative, (val) => {
  if (val) setNativeLanguage(val)
})

watch(localTarget, (val) => {
  if (val) setTargetLanguage(val)
})

// Load situations and languages when modal opens
watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      // Load languages from backend
      languages.value = await loadLanguages()

      // Sync with global settings
      localNative.value = settings.value.nativeLanguage
      localTarget.value = settings.value.targetLanguage

      // Load situations
      loadSituations()
    } else {
      searchQuery.value = ''
      showCreateField.value = false
    }
  }
)
</script>

<template>
  <div class="h-screen flex flex-col">
    <!-- Header with situation selector button -->
    <div class="navbar bg-base-200 shadow-sm">
      <div class="flex-1 gap-2">
        <button class="btn btn-sm" @click="showSituationPicker = true">
          {{ situationDisplay }}
        </button>
      </div>
    </div>

    <!-- Situation Picker Modal -->
    <SituationPicker
      :open="showSituationPicker"
      @close="showSituationPicker = false"
      @select="changeSituation"
    />

    <!-- Tab navigation -->
    <div class="tabs tabs-boxed bg-base-200 px-4 pt-2">
      <button
        class="tab"
        :class="{ 'tab-active': activeTab === 'overview' }"
        @click="activeTab = 'overview'"
      >
        <List class="w-4 h-4 mr-2" />
        Overview
      </button>
      <button
        v-for="goal in goals"
        :key="goal.id"
        class="tab"
        :class="{ 'tab-active': activeTab === goal.id }"
        @click="activeTab = goal.id"
      >
        {{ goal.title }}
      </button>
    </div>

    <!-- Tab content -->
    <div class="flex-1 overflow-y-auto p-4">
      <div v-if="loading" class="flex justify-center items-center h-full">
        <span class="loading loading-spinner loading-lg"></span>
      </div>

      <template v-else-if="situation">
        <!-- Overview Tab -->
        <OverviewTab
          v-if="activeTab === 'overview'"
          :situation="situation"
          :goals="goals"
          :native-language="nativeLang"
          :target-language="targetLang"
          @add-goal="addGoal"
          @select-goal="selectGoal"
          @reload-goals="reloadGoals"
        />

        <!-- Goal Tabs -->
        <div v-else>
          <p class="text-base-content/60">
            Goal editor for "{{ goals.find(g => g.id === activeTab)?.title }}" will be implemented in Phase 3.
          </p>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { List } from 'lucide-vue-next'
import OverviewTab from './OverviewTab.vue'
import SituationPicker from '../../features/situation-picker/SituationPicker.vue'
import { useToasts } from '../../features/toast-center/useToasts'
import { loadLanguages, getLanguageSymbol } from '../../entities/languages/loader'
import { useSettings } from '../../entities/system/settingsStore'
import type { Language } from '../../entities/languages/types'
import { detectGoalType } from '../../entities/glosses/goalState'

interface Situation {
  slug: string
  content: string
  language: string
  tags: string[]
  children?: string[]
}

interface Goal {
  id: string
  title: string
  type: 'procedural' | 'understanding'
  state: 'red' | 'yellow' | 'green'
}

const route = useRoute()
const router = useRouter()
const { error } = useToasts()
const { settings } = useSettings()

const situation = ref<Situation | null>(null)
const goals = ref<Goal[]>([])
const activeTab = ref<string>('overview')
const loading = ref(false)
const showSituationPicker = ref(false)
const languages = ref<Language[]>([])

// Extract language params from route
const nativeLang = computed(() => route.params.nativeLang as string)
const targetLang = computed(() => route.params.targetLang as string)

// Display format: "situation content native→target"
const situationDisplay = computed(() => {
  if (!situation.value || !nativeLang.value || !targetLang.value || languages.value.length === 0) {
    return 'Loading...'
  }

  const nativeSymbol = getLanguageSymbol(nativeLang.value, languages.value)
  const targetSymbol = getLanguageSymbol(targetLang.value, languages.value)

  return `${situation.value.content} ${nativeSymbol}→${targetSymbol}`
})

async function loadSituation() {
  loading.value = true
  try {
    const situationLang = route.params.situationLang as string
    const situationSlug = route.params.situationSlug as string
    const native = route.params.nativeLang as string
    const target = route.params.targetLang as string

    if (!situationLang || !situationSlug || !native || !target) {
      error('Invalid situation parameters')
      router.push('/')
      return
    }

    situation.value = await window.electronAPI.gloss.load(situationLang, situationSlug)

    if (!situation.value) {
      error('Situation not found')
      router.push('/')
      return
    }

    // Load goals (children of this situation)
    goals.value = await loadGoals(situation.value)
  } catch (err) {
    error('Failed to load situation')
    console.error(err)
    router.push('/')
  } finally {
    loading.value = false
  }
}

async function loadGoals(sit: Situation): Promise<Goal[]> {
  const children = sit.children || []
  const native = nativeLang.value
  const target = targetLang.value

  if (!native || !target) {
    return []
  }

  const goalPromises = children.map(async (ref) => {
    try {
      const gloss = await window.electronAPI.gloss.resolveRef(ref)

      // Detect goal type using language and tags
      const goalType = detectGoalType(gloss, native, target)

      // Skip if not a valid goal for this native/target pair
      if (!goalType) {
        return null
      }

      // Evaluate goal state
      const evaluation = await window.electronAPI.gloss.evaluateGoalState(ref, native, target)

      return {
        id: gloss.slug,
        title: gloss.content,
        type: goalType,
        state: evaluation.state
      }
    } catch (err) {
      console.error('Failed to load goal:', err)
      return null
    }
  })

  const results = await Promise.all(goalPromises)
  return results.filter((g): g is Goal => g !== null)
}

function addGoal() {
  // Will be implemented with goal creation flow
  console.log('Add goal clicked')
}

function selectGoal(goalId: string) {
  activeTab.value = goalId
}

async function reloadGoals() {
  // Reload the situation from disk to get updated children array
  const situationLang = route.params.situationLang as string
  const situationSlug = route.params.situationSlug as string

  const freshSituation = await window.electronAPI.gloss.load(situationLang, situationSlug)
  if (freshSituation) {
    situation.value = freshSituation
    goals.value = await loadGoals(freshSituation)
  }
}

function changeSituation(newSituation: Situation) {
  showSituationPicker.value = false

  // Navigate to new situation, preserving or updating languages from settings
  router.push({
    name: 'situation-workspace',
    params: {
      situationLang: newSituation.language,
      situationSlug: newSituation.slug,
      nativeLang: settings.value.nativeLanguage!,
      targetLang: settings.value.targetLanguage!
    }
  })
}

// Watch for route changes to reload situation
watch(
  () => route.params,
  () => {
    loadSituation()
  }
)

onMounted(async () => {
  // Load languages for display
  languages.value = await loadLanguages()

  // Load the situation
  loadSituation()
})
</script>

<template>
  <div class="h-screen flex flex-col">
    <!-- Header with situation selector button -->
    <div class="navbar bg-base-200 shadow-sm">
      <div class="flex-1 gap-2">
        <button class="btn btn-sm" @click="showSituationPicker = true">
          {{ situationDisplay }}
        </button>
        <button class="btn btn-sm btn-ghost" @click="showSettings = true" title="Settings">
          <Settings class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- Situation Picker Modal -->
    <SituationPicker
      :open="showSituationPicker"
      @close="showSituationPicker = false"
      @select="changeSituation"
    />

    <!-- Settings Modal -->
    <SettingsModal
      :open="showSettings"
      :current-api-key="settings.openaiApiKey"
      @close="showSettings = false"
      @save="saveApiKey"
    />

    <!-- Main content: left sidebar + tab content -->
    <div class="flex-1 flex overflow-hidden">
      <!-- Left sidebar navigation -->
      <div class="w-64 bg-base-200 overflow-y-auto border-r border-base-300">
        <ul class="menu">
          <li>
            <a
              :class="{ active: activeTab === 'overview' }"
              @click="activeTab = 'overview'"
            >
              <List class="w-4 h-4" />
              Overview
            </a>
          </li>
          <li v-for="goal in goals" :key="goal.id">
            <a
              :class="{ active: activeTab === goal.id }"
              @click="activeTab = goal.id"
            >
              <span class="badge badge-outline badge-xs mr-2">
                {{ goal.type === 'procedural' ? 'PROC' : 'UNDR' }}
              </span>
              <span class="flex-1 truncate">{{ goal.title }}</span>
              <span
                class="badge badge-xs"
                :class="{
                  'badge-error': goal.state === 'red',
                  'badge-warning': goal.state === 'yellow',
                  'badge-success': goal.state === 'green'
                }"
              >
                {{ goal.state.toUpperCase() }}
              </span>
            </a>
          </li>
        </ul>
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
          <div v-else class="space-y-4">
            <div class="flex items-center gap-2">
              <h2 class="text-xl font-semibold">
                {{ activeGoalTitle }}
              </h2>
              <span
                class="badge"
                :class="{
                  'badge-error': activeGoalState === 'red',
                  'badge-warning': activeGoalState === 'yellow',
                  'badge-success': activeGoalState === 'green'
                }"
              >
                {{ activeGoalState?.toUpperCase() }}
              </span>
            </div>

            <div v-if="treeLoading" class="flex justify-center py-8">
              <span class="loading loading-spinner loading-lg"></span>
            </div>

            <GlossTreePanel
              v-else
              :nodes="goalNodes"
              @open-gloss="openGloss"
              @delete-gloss="deleteGloss"
              @toggle-exclude="toggleExclude"
              @detach="detachRelation"
            />
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { List, Settings } from 'lucide-vue-next'
import OverviewTab from './OverviewTab.vue'
import SituationPicker from '../../features/situation-picker/SituationPicker.vue'
import SettingsModal from '../../features/settings-modal/SettingsModal.vue'
import GlossTreePanel from '../../features/gloss-tree-panel/GlossTreePanel.vue'
import { useToasts } from '../../features/toast-center/useToasts'
import { getLanguageSymbol, loadLanguages } from '../../entities/languages/loader'
import { useSettings } from '../../entities/system/settingsStore'
import type { Language } from '../../entities/languages/types'
import { buildGoalNodes, type TreeNode } from '../../entities/glosses/treeBuilder'
import type { Gloss } from '../../../main-process/storage/types'
import type { GlossStorage } from '../../../main-process/storage/fsGlossStorage'

interface Goal {
  id: string
  title: string
  type: 'procedural' | 'understanding'
  state: 'red' | 'yellow' | 'green'
}

const route = useRoute()
const router = useRouter()
const { error, success } = useToasts()
const { settings, setOpenAIApiKey } = useSettings()

const situation = ref<Gloss | null>(null)
const goals = ref<Goal[]>([])
const activeTab = ref<string>('overview')
const loading = ref(false)
const treeLoading = ref(false)
const showSituationPicker = ref(false)
const showSettings = ref(false)
const languages = ref<Language[]>([])
const treeNodes = ref<TreeNode[]>([])

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

const activeGoalTitle = computed(() => {
  if (activeTab.value === 'overview') return ''
  return goals.value.find((g) => g.id === activeTab.value)?.title || ''
})

const activeGoalState = computed(() => {
  if (activeTab.value === 'overview') return ''
  return goals.value.find((g) => g.id === activeTab.value)?.state || ''
})

const goalNodes = computed(() => {
  if (activeTab.value === 'overview') return []
  return treeNodes.value.filter(
    (node) => `${node.gloss.language}:${node.gloss.slug}` === activeTab.value
  )
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
    activeTab.value = 'overview'

    if (!situation.value) {
      error('Situation not found')
      router.push('/')
      return
    }

    await refreshTree(situation.value)
  } catch (err) {
    error('Failed to load situation')
    console.error(err)
    router.push('/')
  } finally {
    loading.value = false
  }
}

function addGoal() {
  // Hooked up via Overview tab; placeholder here for future goal creation modal
  console.log('Add goal clicked')
}

function selectGoal(goalId: string) {
  activeTab.value = goalId
}

async function reloadGoals() {
  if (!situation.value) return
  await refreshTree(situation.value)
}

function changeSituation(newSituation: Gloss) {
  showSituationPicker.value = false

  const native = settings.value.nativeLanguage
  const target = settings.value.targetLanguage

  if (!native || !target) {
    error('Select native and target languages first')
    return
  }

  // Navigate to new situation, preserving or updating languages from settings
  router.push({
    name: 'situation-workspace',
    params: {
      situationLang: newSituation.language,
      situationSlug: newSituation.slug,
      nativeLang: native,
      targetLang: target
    }
  })
}

async function saveApiKey(apiKey: string) {
  try {
    await setOpenAIApiKey(apiKey)
    success('API key saved')
  } catch (err) {
    error('Failed to save API key')
    console.error(err)
  }
}

async function loadGlossGraph(startRefs: string[]): Promise<Map<string, Gloss>> {
  const queue = [...startRefs]
  const graph = new Map<string, Gloss>()

  while (queue.length) {
    const ref = queue.shift()
    if (!ref || graph.has(ref)) continue

    const gloss = await window.electronAPI.gloss.resolveRef(ref)
    if (!gloss) continue

    const slug = gloss.slug || ref.split(':').slice(1).join(':')
    const key = `${gloss.language}:${slug}`
    graph.set(key, { ...gloss, slug })

    const neighbors = [
      ...(gloss.parts || []),
      ...(gloss.translations || []),
      ...(gloss.usage_examples || [])
    ]
    for (const n of neighbors) {
      if (!graph.has(n)) {
        queue.push(n)
      }
    }
  }

  return graph
}

function mapGoalsFromNodes(nodes: TreeNode[]): Goal[] {
  const order: Record<Goal['type'], number> = { procedural: 0, understanding: 1 }

  return nodes
    .filter((node) => node.goal_type)
    .map((node) => ({
      id: `${node.gloss.language}:${node.gloss.slug}`,
      title: node.gloss.content,
      type: node.goal_type === 'procedural' ? 'procedural' : 'understanding',
      state: node.state || 'red'
    }))
    .sort((a, b) => {
      if (a.type !== b.type) return order[a.type] - order[b.type]
      return a.title.localeCompare(b.title)
    })
}

async function refreshTree(currentSituation: Gloss) {
  if (!nativeLang.value || !targetLang.value) return
  treeLoading.value = true
  try {
    const children = currentSituation.children || []
    const graph = await loadGlossGraph(children)

    const storage: Pick<GlossStorage, 'resolveReference'> = {
      resolveReference(ref: string) {
        return graph.get(ref) || null
      }
    }

    const { nodes } = buildGoalNodes(
      currentSituation,
      storage as GlossStorage,
      nativeLang.value,
      targetLang.value
    )

    treeNodes.value = nodes
    goals.value = mapGoalsFromNodes(nodes)

    // Ensure the active tab still exists
    if (activeTab.value !== 'overview') {
      const exists = goals.value.some((g) => g.id === activeTab.value)
      if (!exists) {
        activeTab.value = 'overview'
      }
    }
  } catch (err) {
    console.error('Failed to refresh tree', err)
    error('Failed to load goal tree')
  } finally {
    treeLoading.value = false
  }
}

async function openGloss(ref: string) {
  // Placeholder until GlossModal is wired
  console.log('Open gloss modal for', ref)
}

async function deleteGloss(ref: string) {
  const [language, ...slugParts] = ref.split(':')
  const slug = slugParts.join(':')
  if (!language || !slug) return

  try {
    await window.electronAPI.gloss.deleteWithCleanup(language, slug)
    success('Gloss deleted')
    if (situation.value) {
      await refreshTree(situation.value)
    }
  } catch (err) {
    console.error('Failed to delete gloss', err)
    error('Delete failed')
  }
}

async function toggleExclude(ref: string) {
  try {
    const gloss = await window.electronAPI.gloss.resolveRef(ref)
    if (!gloss) return
    gloss.excludeFromLearning = !gloss.excludeFromLearning
    await window.electronAPI.gloss.save(gloss)
    success(gloss.excludeFromLearning ? 'Excluded from learning' : 'Included in learning')
    if (situation.value) {
      await refreshTree(situation.value)
    }
  } catch (err) {
    console.error('Failed to toggle exclude', err)
    error('Toggle failed')
  }
}

async function detachRelation(parentRef: string, field: string, childRef: string) {
  if (!parentRef || !field || !childRef) {
    error('Cannot detach: missing relation context')
    return
  }
  try {
    await window.electronAPI.gloss.detachRelation(parentRef, field, childRef)
    success('Detached relation')
    if (situation.value) {
      await refreshTree(situation.value)
    }
  } catch (err) {
    console.error('Failed to detach relation', err)
    error('Detach failed')
  }
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
  await loadSituation()
})
</script>

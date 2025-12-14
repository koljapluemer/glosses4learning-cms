<template>
  <div class="h-screen flex flex-col">
    <h1 class="sr-only">Situation Workspace</h1>
    <!-- Header with situation selector button -->
    <div class="navbar bg-base-200 shadow-sm">
      <div class="flex-1 flex items-center gap-2">
        <button class="btn btn-sm btn-ghost btn-square" title="Home" @click="goHome">
          <Home class="w-4 h-4" />
        </button>
        <button class="btn btn-sm" @click="showSituationPicker = true">
          {{ situationDisplay }}
        </button>
        <button class="btn btn-sm btn-ghost btn-square" :disabled="loading || treeLoading" @click="refreshWorkspace" title="Refresh">
          <RefreshCw class="w-4 h-4" :class="{ 'animate-spin': treeLoading }" />
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
      @open-gloss="openSituationGloss"
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
                  'badge-warning': goal.state === 'yellow'
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
            @detach-goal="detachGoal"
            @delete-goal="deleteGoal"
            @edit-goal="openGloss"
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
                  'badge-warning': activeGoalState === 'yellow'
                }"
              >
                {{ activeGoalState?.toUpperCase() }}
              </span>
              <button
                v-if="activeGoalState === 'red'"
                class="btn btn-ghost btn-xs"
                title="Show missing requirements"
                :disabled="stateLogLoading"
                @click="openStateLog"
              >
                <Info class="w-4 h-4" />
              </button>
            </div>

            <div v-if="treeLoading" class="flex justify-center py-8">
              <span class="loading loading-spinner loading-lg"></span>
            </div>

            <GlossTreePanel
              v-else
              :nodes="goalNodes"
              :expanded-refs="expandedRefs"
              @open-gloss="openGloss"
              @delete-gloss="deleteGloss"
              @toggle-exclude="toggleExclude"
              @detach="detachRelation"
              @toggle-expand="onToggleExpand"
            />

            <div class="flex flex-wrap items-center gap-3">
              <div class="badge badge-outline">Legend</div>
              <div class="flex items-center gap-1 text-sm">
                <span class="badge badge-outline badge-xs">PROC</span><span>Procedural goal</span>
              </div>
              <div class="flex items-center gap-1 text-sm">
                <span class="badge badge-outline badge-xs">UNDR</span><span>Understanding goal</span>
              </div>
              <div class="flex items-center gap-1 text-sm">
                <Layers class="w-3 h-3" /><span>Part</span>
              </div>
              <div class="flex items-center gap-1 text-sm">
                <Languages class="w-3 h-3" /><span>Translation</span>
              </div>
              <div class="flex items-center gap-1 text-sm">
                <MessageSquareWarning class="w-3 h-3 text-warning" /><span>Usage missing</span>
              </div>
              <div class="flex items-center gap-1 text-sm">
                <Languages class="w-3 h-3 text-warning" /><span>Translation missing</span>
              </div>
              <div class="flex items-center gap-1 text-sm">
                <Layers class="w-3 h-3 text-warning" /><span>Parts missing</span>
              </div>
            </div>

            <div class="flex gap-2">
              <button class="btn btn-sm" @click="expandAll">Expand all</button>
              <button class="btn btn-sm" @click="collapseAll">Collapse all</button>
            </div>

            <AiBatchToolPanel
              v-if="activeGoalRef"
              :goal-ref="activeGoalRef"
              :goal-kind="activeGoalKind"
              :native-language="nativeLang"
              :target-language="targetLang"
              :missing-native-refs="goalStats.missingNative"
              :missing-target-refs="goalStats.missingTarget"
              :missing-parts-refs="goalStats.missingParts"
              :missing-usage-refs="goalStats.missingUsage"
              @applied="handleGlossSaved"
            />
          </div>
        </template>
      </div>
    </div>

    <!-- Gloss modal lives at root so it can be opened from anywhere -->
<GlossModal
  :open="glossModalOpen"
  :gloss-ref="activeGlossRef"
  :native-language="nativeLang"
  :target-language="targetLang"
  @close="glossModalOpen = false"
  @saved="handleGlossSaved"
  @deleted="handleGlossDeleted"
/>

<!-- Goal state log modal -->
<dialog :open="showStateLog" class="modal">
  <div class="modal-box max-w-3xl">
    <h3 class="font-semibold text-lg mb-3">Goal requirements</h3>
    <pre class="whitespace-pre-wrap text-sm bg-base-200 p-3 rounded">{{ stateLog }}</pre>
    <div class="modal-action">
      <button class="btn" @click="showStateLog = false">Close</button>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop" @submit="showStateLog = false">
    <button>close</button>
  </form>
</dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Home,
  List,
  Settings,
  Info,
  Layers,
  Languages,
  MessageSquareWarning,
  RefreshCw
} from 'lucide-vue-next'
import OverviewTab from './OverviewTab.vue'
import SituationPicker from '../../features/situation-picker/SituationPicker.vue'
import SettingsModal from '../../features/settings-modal/SettingsModal.vue'
import GlossTreePanel from '../../features/gloss-tree-panel/GlossTreePanel.vue'
import GlossModal from '../../features/gloss-modal/GlossModal.vue'
import AiBatchToolPanel from '../../features/ai-batch-tools/AiBatchToolPanel.vue'
import { useToasts } from '../../features/toast-center/useToasts'
import { getLanguageSymbol, loadLanguages } from '../../entities/languages/loader'
import { useSettings } from '../../entities/system/settingsStore'
import type { Language } from '../../entities/languages/types'
import { buildGoalNodes, type TreeNode, type TreeStats } from '../../entities/glosses/treeBuilder'
import type { Gloss } from '../../../main-process/storage/types'
import type { GlossStorage } from '../../../main-process/storage/fsGlossStorage'

interface Goal {
  id: string
  title: string
  type: 'procedural' | 'understanding'
  state: 'red' | 'yellow'
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
const treeStats = ref<TreeStats | null>(null)
const glossModalOpen = ref(false)
const activeGlossRef = ref<string | null>(null)
const showStateLog = ref(false)
const stateLog = ref('')
const stateLogLoading = ref(false)
const expandedRefs = ref<Record<string, boolean>>({})

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

const activeGoalKind = computed(() => {
  if (activeTab.value === 'overview') return null
  return goals.value.find((g) => g.id === activeTab.value)?.type || null
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

const activeGoalRef = computed(() => {
  if (activeTab.value === 'overview') return null
  return activeTab.value
})

const goalStats = computed(() => {
  const stats = treeStats.value
  if (!stats || activeTab.value === 'overview') {
    return {
      missingNative: [] as string[],
      missingTarget: [] as string[],
      missingParts: [] as string[],
      missingUsage: [] as string[]
    }
  }
  const goalRootRef = activeTab.value
  const perGoal = stats.goal_missing_by_root[goalRootRef]
  if (!perGoal) {
    return {
      missingNative: [] as string[],
      missingTarget: [] as string[],
      missingParts: [] as string[],
      missingUsage: [] as string[]
    }
  }
  const toArray = (set: Set<string>) => Array.from(set)
  return {
    missingNative: toArray(perGoal.native_missing),
    missingTarget: toArray(perGoal.target_missing),
    missingParts: toArray(perGoal.parts_missing),
    missingUsage: toArray(perGoal.usage_missing)
  }
})

function expansionStorageKey(goalId: string) {
  return `treeExpansion:${goalId}`
}

function loadExpansionState(goalId: string) {
  try {
    const raw = localStorage.getItem(expansionStorageKey(goalId))
    expandedRefs.value = raw ? (JSON.parse(raw) as Record<string, boolean>) : {}
  } catch {
    expandedRefs.value = {}
  }
}

function saveExpansionState(goalId: string) {
  try {
    localStorage.setItem(expansionStorageKey(goalId), JSON.stringify(expandedRefs.value))
  } catch (err) {
    console.warn('Failed to persist tree expansion', err)
  }
}

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
  // Open gloss modal when selecting from overview edit
  if (goalId && goalId !== 'overview') {
    activeGlossRef.value = goalId
  }
}

async function detachGoal(goalId: string) {
  if (!situation.value) return
  const parentRef = `${situation.value.language}:${situation.value.slug}`
  try {
    await window.electronAPI.gloss.detachRelation(parentRef, 'children', goalId)
    success('Goal detached')
    await refreshTree(situation.value)
  } catch (err) {
    console.error(err)
    error('Failed to detach goal')
  }
}

async function deleteGoal(goalId: string) {
  const [language, ...slugParts] = goalId.split(':')
  const slug = slugParts.join(':')
  if (!language || !slug) return

  const ok = confirm(`Delete goal ${goalId}? This cleans references.`)
  if (!ok) return
  try {
    await window.electronAPI.gloss.deleteWithCleanup(language, slug)
    success('Goal deleted')
    if (situation.value) {
      await refreshTree(situation.value)
    }
  } catch (err) {
    console.error(err)
    error('Failed to delete goal')
  }
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

function openSituationGloss(situation: Gloss) {
  activeGlossRef.value = `${situation.language}:${situation.slug}`
  glossModalOpen.value = true
}

function goHome() {
  router.push({ name: 'dashboard', query: { noAutoOpen: '1' } })
}

async function refreshWorkspace() {
  if (loading.value || treeLoading.value) return
  try {
    const situationLang = route.params.situationLang as string
    const situationSlug = route.params.situationSlug as string
    if (!situationLang || !situationSlug) {
      error('Invalid situation parameters')
      return
    }

    const latest = await window.electronAPI.gloss.load(situationLang, situationSlug)
    if (!latest) {
      error('Situation not found')
      return
    }

    situation.value = latest
    await refreshTree(latest)
  } catch (err) {
    console.error('Workspace refresh failed', err)
    error('Failed to refresh workspace')
  }
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
      title: node.display,
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

    const { nodes, stats } = buildGoalNodes(
      currentSituation,
      storage as GlossStorage,
      nativeLang.value,
      targetLang.value
    )

    treeNodes.value = nodes
    treeStats.value = stats
    goals.value = mapGoalsFromNodes(nodes)

    // Load stored expansion for active goal
    if (activeTab.value && activeTab.value !== 'overview') {
      loadExpansionState(activeTab.value)
    } else {
      expandedRefs.value = {}
    }

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
  activeGlossRef.value = ref
  glossModalOpen.value = true
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
  let relField = field
  let relParent = parentRef || ''

  function findParent(ref: string, nodes: TreeNode[]): { parent?: string; via?: string } | null {
    for (const node of nodes) {
      for (const child of node.children) {
        const childId = `${child.gloss.language}:${child.gloss.slug}`
        if (childId === ref) {
          return { parent: `${node.gloss.language}:${node.gloss.slug}`, via: child.viaField }
        }
        const deep = findParent(ref, child.children)
        if (deep) return deep
      }
    }
    return null
  }

  if (!relParent) {
    const found = findParent(childRef, treeNodes.value)
    if (found?.parent) {
      relParent = found.parent
      if (!relField && found.via) relField = found.via
    }
  }

  if (!relParent || !relField) {
    const locate = (nodes: TreeNode[]): { parent?: string; via?: string } | null => {
      for (const node of nodes) {
        const id = `${node.gloss.language}:${node.gloss.slug}`
        if (id === childRef) {
          return { parent: node.parentRef, via: node.viaField }
        }
        const deep = locate(node.children)
        if (deep) return deep
      }
      return null
    }
    const details = locate(treeNodes.value)
    if (details?.parent) {
      relParent = details.parent
      if (!relField && details.via) relField = details.via
    }
  }

  if (!relParent || !childRef) {
    error('Cannot detach: missing relation context')
    return
  }

  // Heuristic: if field empty, find which relation includes child
  if (!relField) {
    const parent = await window.electronAPI.gloss.resolveRef(relParent)
    if (!parent) {
      error('Parent not found')
      return
    }
    const relations: Record<string, string[]> = parent as unknown as Record<string, string[]>
    const matchField = Object.keys(relations).find((key) => {
      const val = relations[key]
      return Array.isArray(val) && val.includes(childRef)
    })
    if (!matchField) {
      error('Relation not found on parent')
      return
    }
    relField = matchField
  }
  try {
    await window.electronAPI.gloss.detachRelation(relParent, relField, childRef)
    success('Detached relation')
    if (situation.value) {
      await refreshTree(situation.value)
    }
  } catch (err) {
    console.error('Failed to detach relation', err)
    error('Detach failed')
  }
}

async function handleGlossSaved() {
  if (situation.value) {
    await refreshTree(situation.value)
  }
}

async function handleGlossDeleted(ref?: string) {
  if (ref && situation.value) {
    const situationRef = `${situation.value.language}:${situation.value.slug}`
    if (ref === situationRef) {
      router.push('/')
      return
    }
  }
  if (situation.value) {
    await refreshTree(situation.value)
  }
  glossModalOpen.value = false
}

async function openStateLog() {
  if (!activeGoalRef.value) return
  stateLogLoading.value = true
  try {
    const result = await window.electronAPI.gloss.evaluateGoalState(
      activeGoalRef.value,
      nativeLang.value,
      targetLang.value
    )
    stateLog.value = result.log
    showStateLog.value = true
  } catch (err) {
    console.error('Failed to load goal log', err)
    error('Could not load goal state details')
  } finally {
    stateLogLoading.value = false
  }
}

function onToggleExpand(ref: string, expanded: boolean) {
  expandedRefs.value = { ...expandedRefs.value, [ref]: expanded }
  if (activeGoalRef.value) {
    saveExpansionState(activeGoalRef.value)
  }
}

function collectRefs(nodes: TreeNode[]): string[] {
  const refs: string[] = []
  const walk = (n: TreeNode) => {
    const ref = `${n.gloss.language}:${n.gloss.slug}`
    refs.push(ref)
    for (const child of n.children || []) {
      walk(child)
    }
  }
  nodes.forEach(walk)
  return refs
}

function expandAll() {
  if (!goalNodes.value.length) return
  const refs = collectRefs(goalNodes.value)
  const next: Record<string, boolean> = {}
  refs.forEach((r) => {
    next[r] = true
  })
  expandedRefs.value = next
  if (activeGoalRef.value) saveExpansionState(activeGoalRef.value)
}

function collapseAll() {
  expandedRefs.value = {}
  if (activeGoalRef.value) saveExpansionState(activeGoalRef.value)
}

// Watch for route changes to reload situation
watch(
  () => route.params,
  () => {
    loadSituation()
  }
)

watch(
  () => activeTab.value,
  (val) => {
    if (val && val !== 'overview') {
      loadExpansionState(val)
    } else {
      expandedRefs.value = {}
    }
  }
)

onMounted(async () => {
  // Load languages for display
  languages.value = await loadLanguages()

  // Load the situation
  await loadSituation()
})
</script>

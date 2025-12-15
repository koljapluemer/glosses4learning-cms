<template>
  <div class="space-y-6">
    <!-- Situation Info -->
    <div class="flex items-center justify-between">
      <div>
        <div class="text-sm text-light">Situation</div>
        <div class="font-medium">{{ situation.content }}</div>
      </div>
      <button class="btn btn-sm" @click="editSituation">
        Edit situation
      </button>
    </div>

    <!-- Goals Table -->
    <div v-if="goals.length > 0" class="overflow-x-auto">
      <table class="table">
        <thead>
          <tr>
            <th>Content</th>
            <th>Type</th>
            <th>State</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="goal in goals" :key="goal.id">
            <td>{{ goal.title }}</td>
            <td class="text-sm">
              <span v-if="goal.type === 'understanding'" class="badge badge-sm">UNDR</span>
              <span v-else-if="goal.type === 'procedural'" class="badge badge-sm">PROC</span>
            </td>
            <td>
              <span class="badge badge-sm" :class="{
                'badge-error': goal.state === 'red',
                'badge-warning': goal.state === 'yellow'
              }">
                {{ goal.state?.toUpperCase() || 'PENDING' }}
              </span>
            </td>
            <td>
              <div class="flex gap-1">
                <button class="btn btn-ghost btn-xs" @click="$emit('select-goal', goal.id)" title="Open tab">
                  <ExternalLink class="w-4 h-4" />
                </button>
                <button class="btn btn-ghost btn-xs" title="Disattach" @click="$emit('detach-goal', goal.id)">
                  <Unlink class="w-4 h-4" />
                </button>
                <button class="btn btn-ghost btn-xs text-error" title="Delete" @click="$emit('delete-goal', goal.id)">
                  <Trash2 class="w-4 h-4" />
                </button>
                <button class="btn btn-ghost btn-xs" title="Edit" @click="$emit('edit-goal', goal.id)">
                  <Edit class="w-4 h-4" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Manual Goal Addition -->
    <div class="grid grid-cols-2 gap-4">
      <fieldset class="fieldset">
        <label class="label">Procedural (native)</label>
        <input
          v-model="proceduralInput"
          type="text"
          class="input input-bordered w-full"
          placeholder="Enter paraphrased expression..."
          @keyup.enter="addProceduralGoal"
        />
      </fieldset>

      <fieldset class="fieldset">
        <label class="label">Understanding (target)</label>
        <input
          v-model="understandingInput"
          type="text"
          class="input input-bordered w-full"
          placeholder="Enter target expression..."
          @keyup.enter="addUnderstandingGoal"
        />
      </fieldset>
    </div>

    <!-- AI Tools -->
    <div class="space-y-3">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
        <fieldset class="fieldset">
          <label class="label">How many</label>
          <input
            v-model.number="goalCount"
            type="number"
            min="1"
            max="20"
            class="input input-bordered input-sm w-full"
          />
        </fieldset>
        <fieldset class="fieldset md:col-span-2">
          <label class="label">Context (optional)</label>
          <input
            v-model="goalContext"
            type="text"
            class="input input-bordered input-sm w-full"
            placeholder="e.g. business trip, with kids, formal tone"
          />
        </fieldset>
      </div>

      <div class="flex gap-2">
        <button class="btn btn-sm" :disabled="aiGenerating" @click="generateUnderstandingGoals">
          Add Understand Goals
        </button>
        <button class="btn btn-sm" :disabled="aiGenerating" @click="generateProceduralGoals">
          Add Procedural Goals
        </button>
      </div>
    </div>

    <!-- Goal Confirmation Modal -->
    <GoalConfirmModal
      :open="showGoalModal"
      :title="modalTitle"
      :message="modalMessage"
      :goals="generatedGoals"
      :loading="aiGenerating"
      :error="aiError"
      @close="closeGoalModal"
      @confirm="confirmGoals"
    />

    <!-- Situation Gloss Modal -->
    <GlossModal
      :open="showSituationModal"
      :gloss-ref="situationRef"
      :native-language="nativeLanguage"
      :target-language="targetLanguage"
      @close="showSituationModal = false"
      @saved="handleSituationSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ExternalLink, Unlink, Trash2, Edit } from 'lucide-vue-next'
import { useToasts } from '../../features/toast-center/useToasts'
import { useSettings } from '../../entities/system/settingsStore'
import { generateUnderstandingGoals as aiGenerateUnderstanding, generateProceduralGoals as aiGenerateProcedural } from '../../entities/ai/goalGenerator'
import GoalConfirmModal from '../../features/goal-confirm-modal/GoalConfirmModal.vue'
import GlossModal from '../../features/gloss-modal/GlossModal.vue'

interface Situation {
  slug: string
  content: string
  language: string
}

interface Goal {
  id: string
  title: string
  type?: 'understanding' | 'procedural'
  state?: 'red' | 'yellow'
}

const props = defineProps<{
  situation: Situation
  goals: Goal[]
  nativeLanguage: string
  targetLanguage: string
}>()

const emit = defineEmits<{
  'add-goal': []
  'select-goal': [goalId: string]
  'reload-goals': []
  'detach-goal': [goalId: string]
  'delete-goal': [goalId: string]
  'edit-goal': [goalId: string]
}>()

const { success, error } = useToasts()
const { settings } = useSettings()

const proceduralInput = ref('')
const understandingInput = ref('')
const goalCount = ref(5)
const goalContext = ref('')

// AI goal generation state
const showGoalModal = ref(false)
const modalTitle = ref('')
const modalMessage = ref('')
const generatedGoals = ref<string[]>([])
const aiGenerating = ref(false)
const aiError = ref<string | null>(null)
const pendingGoalType = ref<'procedural' | 'understanding' | null>(null)

// Situation modal state
const showSituationModal = ref(false)
const situationRef = computed(() => `${props.situation.language}:${props.situation.slug}`)

/**
 * Add a procedural goal (native language paraphrase expression)
 * Python ref: agent/tools/database/add_gloss_procedural.py:25-42
 */
async function addProceduralGoal() {
  const content = proceduralInput.value.trim()
  if (!content) return

  try {
    // 1. Create or find the gloss in native language
    const gloss = await window.electronAPI.gloss.ensure(props.nativeLanguage, content)

    // 2. Ensure tags are present
    const tags = gloss.tags || []
    let modified = false
    if (!tags.includes('eng:paraphrase')) {
      tags.push('eng:paraphrase')
      modified = true
    }
    if (!tags.includes('eng:procedural-paraphrase-expression-goal')) {
      tags.push('eng:procedural-paraphrase-expression-goal')
      modified = true
    }

    if (modified) {
      gloss.tags = tags
      await window.electronAPI.gloss.save(gloss)
    }

    // 3. Attach to situation as child
    const situationRef = `${props.situation.language}:${props.situation.slug}`
    const goalRef = `${gloss.language}:${gloss.slug}`
    await window.electronAPI.gloss.attachRelation(situationRef, 'children', goalRef)

    success(`Added procedural goal: ${content}`)
    proceduralInput.value = ''
    emit('reload-goals')
  } catch (err) {
    error(`Failed to add procedural goal: ${err}`)
    console.error(err)
  }
}

/**
 * Add an understanding goal (target language expression)
 * Python ref: agent/tools/database/add_gloss_understanding.py:25-42
 */
async function addUnderstandingGoal() {
  const content = understandingInput.value.trim()
  if (!content) return

  try {
    // 1. Create or find the gloss in target language
    const gloss = await window.electronAPI.gloss.ensure(props.targetLanguage, content)

    // 2. Ensure tag is present
    const tags = gloss.tags || []
    if (!tags.includes('eng:understand-expression-goal')) {
      tags.push('eng:understand-expression-goal')
      gloss.tags = tags
      await window.electronAPI.gloss.save(gloss)
    }

    // 3. Attach to situation as child
    const situationRef = `${props.situation.language}:${props.situation.slug}`
    const goalRef = `${gloss.language}:${gloss.slug}`
    await window.electronAPI.gloss.attachRelation(situationRef, 'children', goalRef)

    success(`Added understanding goal: ${content}`)
    understandingInput.value = ''
    emit('reload-goals')
  } catch (err) {
    error(`Failed to add understanding goal: ${err}`)
    console.error(err)
  }
}

/**
 * Generate understanding goals using AI
 * Python ref: agent/tools/llm/generate_understanding_goals.py:57-148
 */
async function generateUnderstandingGoals() {
  const apiKey = settings.value.openaiApiKey
  if (!apiKey) {
    error('OpenAI API key not set. Please configure it in settings.')
    return
  }

  aiGenerating.value = true
  aiError.value = null
  showGoalModal.value = true
  modalTitle.value = 'Generate Understanding Goals'
  modalMessage.value = 'Generating expressions you might encounter in the target language...'
  pendingGoalType.value = 'understanding'
  generatedGoals.value = []

  try {
    const result = await aiGenerateUnderstanding(
      apiKey,
      props.situation.content,
      props.targetLanguage,
      goalCount.value || 5,
      goalContext.value
    )
    generatedGoals.value = result.goals
    modalMessage.value = result.message
  } catch (err) {
    aiError.value = err instanceof Error ? err.message : 'Failed to generate goals'
    console.error(err)
  } finally {
    aiGenerating.value = false
  }
}

/**
 * Generate procedural goals using AI
 * Python ref: agent/tools/llm/generate_procedural_goals.py:52-150
 */
async function generateProceduralGoals() {
  const apiKey = settings.value.openaiApiKey
  if (!apiKey) {
    error('OpenAI API key not set. Please configure it in settings.')
    return
  }

  aiGenerating.value = true
  aiError.value = null
  showGoalModal.value = true
  modalTitle.value = 'Generate Procedural Goals'
  modalMessage.value = 'Generating expressions you might want to say...'
  pendingGoalType.value = 'procedural'
  generatedGoals.value = []

  try {
    const result = await aiGenerateProcedural(
      apiKey,
      props.situation.content,
      props.nativeLanguage,
      props.targetLanguage,
      goalCount.value || 5,
      goalContext.value
    )
    generatedGoals.value = result.goals
    modalMessage.value = result.message
  } catch (err) {
    aiError.value = err instanceof Error ? err.message : 'Failed to generate goals'
    console.error(err)
  } finally {
    aiGenerating.value = false
  }
}

function closeGoalModal() {
  showGoalModal.value = false
  generatedGoals.value = []
  aiError.value = null
  pendingGoalType.value = null
}

function editSituation() {
  showSituationModal.value = true
}

function handleSituationSaved() {
  success('Situation updated')
}

/**
 * Confirm and add selected goals
 */
async function confirmGoals(selectedGoals: string[]) {
  const goalType = pendingGoalType.value
  if (!goalType) return

  closeGoalModal()

  let successCount = 0
  let failCount = 0

  for (const goalContent of selectedGoals) {
    try {
      if (goalType === 'procedural') {
        // Add as procedural goal
        const gloss = await window.electronAPI.gloss.ensure(props.nativeLanguage, goalContent)
        const tags = gloss.tags || []
        let modified = false
        if (!tags.includes('eng:paraphrase')) {
          tags.push('eng:paraphrase')
          modified = true
        }
        if (!tags.includes('eng:procedural-paraphrase-expression-goal')) {
          tags.push('eng:procedural-paraphrase-expression-goal')
          modified = true
        }
        if (modified) {
          gloss.tags = tags
          await window.electronAPI.gloss.save(gloss)
        }
        const situationRef = `${props.situation.language}:${props.situation.slug}`
        const goalRef = `${gloss.language}:${gloss.slug}`
        await window.electronAPI.gloss.attachRelation(situationRef, 'children', goalRef)
      } else {
        // Add as understanding goal
        const gloss = await window.electronAPI.gloss.ensure(props.targetLanguage, goalContent)
        const tags = gloss.tags || []
        if (!tags.includes('eng:understand-expression-goal')) {
          tags.push('eng:understand-expression-goal')
          gloss.tags = tags
          await window.electronAPI.gloss.save(gloss)
        }
        const situationRef = `${props.situation.language}:${props.situation.slug}`
        const goalRef = `${gloss.language}:${gloss.slug}`
        await window.electronAPI.gloss.attachRelation(situationRef, 'children', goalRef)
      }
      successCount++
    } catch (err) {
      console.error('Failed to add goal:', goalContent, err)
      failCount++
    }
  }

  if (successCount > 0) {
    success(`Added ${successCount} goal${successCount !== 1 ? 's' : ''}`)
    emit('reload-goals')
  }
  if (failCount > 0) {
    error(`Failed to add ${failCount} goal${failCount !== 1 ? 's' : ''}`)
  }
}
</script>

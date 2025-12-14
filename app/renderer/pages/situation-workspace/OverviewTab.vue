<template>
  <div class="space-y-6">
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
                'badge-warning': goal.state === 'yellow',
                'badge-success': goal.state === 'green'
              }">
                {{ goal.state?.toUpperCase() || 'PENDING' }}
              </span>
            </td>
            <td>
              <div class="flex gap-1">
                <button class="btn btn-ghost btn-xs" @click="$emit('select-goal', goal.id)" title="Open tab">
                  <ExternalLink class="w-4 h-4" />
                </button>
                <button class="btn btn-ghost btn-xs" title="Disattach">
                  <Unlink class="w-4 h-4" />
                </button>
                <button class="btn btn-ghost btn-xs text-error" title="Delete">
                  <Trash2 class="w-4 h-4" />
                </button>
                <button class="btn btn-ghost btn-xs" title="Edit">
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
    <div class="flex gap-2">
      <button class="btn btn-sm">Add Understand Goals</button>
      <button class="btn btn-sm">Add Procedural Goals</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ExternalLink, Unlink, Trash2, Edit } from 'lucide-vue-next'
import { useToasts } from '../../features/toast-center/useToasts'

interface Situation {
  slug: string
  content: string
  language: string
}

interface Goal {
  id: string
  title: string
  type?: 'understanding' | 'procedural'
  state?: 'red' | 'yellow' | 'green'
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
}>()

const { success, error } = useToasts()
const proceduralInput = ref('')
const understandingInput = ref('')

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
</script>

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

defineProps<{
  situation: Situation
  goals: Goal[]
}>()

defineEmits<{
  'add-goal': []
  'select-goal': [goalId: string]
}>()

const proceduralInput = ref('')
const understandingInput = ref('')

function addProceduralGoal() {
  if (!proceduralInput.value.trim()) return
  // TODO: Create gloss in native language, tag with eng:procedural-paraphrase-expression-goal, attach to situation
  proceduralInput.value = ''
}

function addUnderstandingGoal() {
  if (!understandingInput.value.trim()) return
  // TODO: Create gloss in target language, tag with eng:understand-expression-goal, attach to situation
  understandingInput.value = ''
}
</script>

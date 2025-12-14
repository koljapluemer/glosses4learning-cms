<template>
  <dialog :open="open" class="modal">
    <div class="modal-box max-w-2xl">
      <h3 class="font-bold text-lg mb-4">{{ title }}</h3>

      <p class="text-sm text-base-content/70 mb-4">{{ message }}</p>

      <div v-if="loading" class="flex justify-center py-8">
        <span class="loading loading-spinner loading-lg"></span>
      </div>

      <div v-else-if="error" class="alert alert-error mb-4">
        <span>{{ error }}</span>
      </div>

      <div v-else class="space-y-2 mb-4 max-h-96 overflow-y-auto">
        <label
          v-for="(goal, index) in goals"
          :key="index"
          class="flex items-start gap-3 p-3 rounded-lg hover:bg-base-200 cursor-pointer"
        >
          <input
            type="checkbox"
            class="checkbox checkbox-sm mt-1"
            :checked="selectedGoals.has(index)"
            @change="toggleGoal(index)"
          />
          <span class="flex-1">{{ goal }}</span>
        </label>
      </div>

      <div class="modal-action">
        <button class="btn btn-ghost" @click="$emit('close')">Cancel</button>
        <button
          class="btn btn-primary"
          :disabled="selectedGoals.size === 0 || loading"
          @click="confirmSelection"
        >
          Add {{ selectedGoals.size }} Goal{{ selectedGoals.size !== 1 ? 's' : '' }}
        </button>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop" @submit="$emit('close')">
      <button type="submit">close</button>
    </form>
  </dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  open: boolean
  title: string
  message: string
  goals: string[]
  loading?: boolean
  error?: string | null
}>()

const emit = defineEmits<{
  close: []
  confirm: [selectedGoals: string[]]
}>()

const selectedGoals = ref<Set<number>>(new Set())

// Pre-select all goals when modal opens
watch(
  () => props.goals,
  (newGoals) => {
    selectedGoals.value = new Set(newGoals.map((_, i) => i))
  },
  { immediate: true }
)

function toggleGoal(index: number) {
  if (selectedGoals.value.has(index)) {
    selectedGoals.value.delete(index)
  } else {
    selectedGoals.value.add(index)
  }
}

function confirmSelection() {
  const selected = Array.from(selectedGoals.value)
    .map((i) => props.goals[i])
    .filter(Boolean)
  emit('confirm', selected)
}
</script>

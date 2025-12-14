<template>
  <dialog :open="open" class="modal">
    <div class="modal-box">
      <h3 class="font-bold text-lg mb-4">Settings</h3>

      <div class="space-y-4">
        <!-- OpenAI API Key -->
        <div class="form-control">
          <label class="label">
            <span class="label-text">OpenAI API Key</span>
          </label>
          <input
            v-model="apiKey"
            type="password"
            class="input input-bordered"
            placeholder="sk-..."
          />
          <label class="label">
            <span class="label-text-alt">Required for AI goal generation features</span>
          </label>
        </div>
      </div>

      <div class="modal-action">
        <button class="btn btn-ghost" @click="$emit('close')">Cancel</button>
        <button class="btn btn-primary" @click="saveSettings">Save</button>
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
  currentApiKey: string | null
}>()

const emit = defineEmits<{
  close: []
  save: [apiKey: string]
}>()

const apiKey = ref('')

// Load current API key when modal opens
watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      apiKey.value = props.currentApiKey || ''
    }
  }
)

function saveSettings() {
  emit('save', apiKey.value)
  emit('close')
}
</script>

<template>
  <div class="flex items-center gap-2">
    <input
      ref="inputRef"
      v-model="localValue"
      type="text"
      :placeholder="placeholder"
      class="input input-sm input-bordered flex-1"
      @keydown.enter="handleSubmit"
      @keydown.escape="handleCancel"
    />
    <button
      class="btn btn-sm btn-primary"
      :disabled="!localValue.trim()"
      @click="handleSubmit"
    >
      <Plus class="w-4 h-4" />
    </button>
    <button class="btn btn-sm btn-ghost" @click="handleCancel">
      <X class="w-4 h-4" />
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Plus, X } from 'lucide-vue-next'

const props = defineProps<{
  placeholder?: string
  autofocus?: boolean
}>()

const emit = defineEmits<{
  submit: [value: string]
  cancel: []
}>()

const localValue = ref('')
const inputRef = ref<HTMLInputElement | null>(null)

function handleSubmit() {
  const trimmed = localValue.value.trim()
  if (trimmed) {
    emit('submit', trimmed)
    localValue.value = ''
  }
}

function handleCancel() {
  localValue.value = ''
  emit('cancel')
}

onMounted(() => {
  if (props.autofocus && inputRef.value) {
    inputRef.value.focus()
  }
})
</script>

<template>
  <div class="toast toast-end">
    <div
      v-for="toast in toasts"
      :key="toast.id"
      class="alert"
      :class="{
        'alert-success': toast.type === 'success',
        'alert-error': toast.type === 'error',
        'alert-info': toast.type === 'info'
      }"
    >
      <span>{{ toast.message }}</span>
      <button class="btn btn-sm btn-ghost" @click="$emit('close', toast.id)">✕</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Toast } from '../features/toast-center/useToasts'

defineProps<{
  toasts: readonly Toast[]
}>()

defineEmits<{
  close: [id: number]
}>()
</script>

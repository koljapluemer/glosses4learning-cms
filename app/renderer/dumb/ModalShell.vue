<template>
  <dialog ref="dialogRef" class="modal">
    <div class="modal-box" :class="sizeClass">
      <form method="dialog">
        <button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">✕</button>
      </form>
      <h3 v-if="title" class="font-bold text-lg mb-4">{{ title }}</h3>
      <slot />
    </div>
    <form method="dialog" class="modal-backdrop">
      <button>close</button>
    </form>
  </dialog>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'

const props = defineProps<{
  open: boolean
  title?: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
}>()

const emit = defineEmits<{
  close: []
}>()

const dialogRef = ref<HTMLDialogElement | null>(null)

const sizeClass = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl'
}[props.size || 'md']

watch(() => props.open, (isOpen) => {
  if (dialogRef.value) {
    if (isOpen) {
      dialogRef.value.showModal()
    } else {
      dialogRef.value.close()
    }
  }
})

onMounted(() => {
  if (dialogRef.value) {
    dialogRef.value.addEventListener('close', () => {
      emit('close')
    })
    if (props.open) {
      dialogRef.value.showModal()
    }
  }
})
</script>

<template>
  <div class="flex items-center gap-2 py-1 hover:bg-base-200" :style="{ paddingLeft: `${depth * 1.5}rem` }">
    <button
      v-if="hasChildren"
      class="btn btn-xs btn-ghost"
      @click="$emit('toggle')"
    >
      <ChevronRight v-if="!expanded" class="w-4 h-4" />
      <ChevronDown v-else class="w-4 h-4" />
    </button>
    <div v-else class="w-8"></div>
    <div class="flex-1 flex items-center gap-2">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ChevronRight, ChevronDown } from 'lucide-vue-next'

defineProps<{
  depth: number
  hasChildren: boolean
  expanded: boolean
}>()

defineEmits<{
  toggle: []
}>()
</script>

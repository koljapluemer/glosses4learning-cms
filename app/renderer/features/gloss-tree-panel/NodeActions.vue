<template>
  <div class="ml-auto flex gap-1">
    <!-- Open gloss modal -->
    <button class="btn btn-ghost btn-xs" title="Open" @click="$emit('open-gloss')">
      <ExternalLink class="w-4 h-4" />
    </button>

    <!-- Toggle exclude from learning -->
    <button
      class="btn btn-ghost btn-xs"
      :class="{ 'text-warning': node.gloss.excludeFromLearning }"
      :title="node.gloss.excludeFromLearning ? 'Include in learning' : 'Exclude from learning'"
      @click="$emit('toggle-exclude')"
    >
      <Ban class="w-4 h-4" />
    </button>

    <!-- Detach from parent -->
    <button class="btn btn-ghost btn-xs" title="Detach" @click="$emit('detach')">
      <Unlink class="w-4 h-4" />
    </button>

    <!-- Delete gloss -->
    <button class="btn btn-ghost btn-xs text-error" title="Delete" @click="$emit('delete-gloss')">
      <Trash2 class="w-4 h-4" />
    </button>
  </div>
</template>

<script setup lang="ts">
import { ExternalLink, Ban, Unlink, Trash2 } from 'lucide-vue-next'
import type { TreeNode } from '../../entities/glosses/treeBuilder'

defineProps<{
  node: TreeNode
}>()

defineEmits<{
  'open-gloss': []
  'delete-gloss': []
  'toggle-exclude': []
  'detach': []
}>()
</script>

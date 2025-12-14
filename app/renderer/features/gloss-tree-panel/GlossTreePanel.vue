<template>
  <div class="space-y-4">
    <!-- Goals tree -->
    <div v-if="nodes.length > 0" class="space-y-2">
      <TreeNodeItem
        v-for="(node, index) in nodes"
        :key="index"
        :node="node"
        :depth="0"
        :expanded-refs="expandedRefs"
        @open-gloss="$emit('open-gloss', $event)"
        @delete-gloss="$emit('delete-gloss', $event)"
        @toggle-exclude="$emit('toggle-exclude', $event)"
        @detach="$emit('detach', $event)"
        @toggle-expand="(ref, expanded) => $emit('toggle-expand', ref, expanded)"
      />
    </div>

    <!-- Empty state -->
    <div v-else class="alert">
      <AlertTriangle class="w-5 h-5" />
      <span>No goals found for this situation</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { AlertTriangle } from 'lucide-vue-next'
import TreeNodeItem from './TreeNodeItem.vue'
import type { TreeNode } from '../../entities/glosses/treeBuilder'

defineProps<{
  nodes: TreeNode[]
  expandedRefs?: Record<string, boolean>
}>()

defineEmits<{
  'open-gloss': [ref: string]
  'delete-gloss': [ref: string]
  'toggle-exclude': [ref: string]
  'detach': [parentRef: string, field: string, childRef: string]
  'toggle-expand': [ref: string, expanded: boolean]
}>()
</script>

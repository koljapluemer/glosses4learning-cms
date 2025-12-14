<template>
  <div class="flex items-center gap-2 flex-wrap">
    <!-- Marker badge (PROC/UNDR/USG) -->
    <span v-if="node.marker" class="badge badge-outline">{{ node.marker }}</span>

    <!-- State badge (RED/YELLOW/GREEN) only on root -->
    <span
      v-if="node.state"
      class="badge uppercase"
      :class="{
        'badge-error': node.state === 'red',
        'badge-warning': node.state === 'yellow',
        'badge-success': node.state === 'green'
      }"
    >
      {{ node.state }}
    </span>

    <!-- Role icon -->
    <component :is="roleIcon" class="w-4 h-4" />

    <!-- Content text -->
    <span
      :class="{
        'font-semibold': node.bold,
        'line-through text-base-300': isStrikethrough
      }"
    >
      {{ node.display }}
    </span>

    <!-- Strikethrough reason badge -->
    <span v-if="isStrikethrough" class="badge badge-xs badge-warning ml-1">
      {{ node.gloss.needsHumanCheck ? 'CHECK' : 'NOLEARN' }}
    </span>

    <!-- Parent badge -->
    <span v-if="node.parentRef" class="badge badge-outline badge-xs">
      parent: {{ node.parentRef }}
    </span>

    <!-- Warning icons -->
    <Languages
      v-if="node.warn_native_missing || node.warn_target_missing"
      class="w-4 h-4 text-warning"
      title="Translation missing"
    />
    <MessageSquareWarning
      v-if="node.warn_usage_missing"
      class="w-4 h-4 text-warning"
      title="Usage missing"
    />
    <Layers v-if="node.warn_parts_missing" class="w-4 h-4 text-warning" title="Parts missing" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  Circle,
  Layers,
  MessageCircle,
  Languages,
  MessageSquareWarning
} from 'lucide-vue-next'
import type { TreeNode } from '../../entities/glosses/treeBuilder'

const props = defineProps<{
  node: TreeNode
}>()

const roleIcon = computed(() => {
  switch (props.node.role) {
    case 'part':
    case 'usage_part':
      return Layers
    case 'usage':
      return MessageCircle
    case 'translation':
      return Languages
    default:
      return Circle
  }
})

const isStrikethrough = computed(
  () => props.node.gloss.needsHumanCheck || props.node.gloss.excludeFromLearning
)
</script>

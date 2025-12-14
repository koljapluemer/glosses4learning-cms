<template>
  <div :style="{ marginLeft: `${depth * 1.25}rem` }">
    <!-- Node with children - collapsible -->
    <div v-if="hasChildren" class="bg-base-100 shadow rounded-box">
      <div class="flex items-center gap-2 flex-wrap px-3 py-2">
        <button
          class="btn btn-ghost btn-xs shrink-0"
          type="button"
          :aria-expanded="isExpanded"
          :aria-label="isExpanded ? 'Collapse children' : 'Expand children'"
          @click="toggleExpanded"
        >
          <ChevronRight
            class="w-4 h-4 transition-transform duration-200"
            :class="{ 'rotate-90': isExpanded }"
          />
        </button>
        <NodeContent :node="node" />
        <NodeActions
          :node="node"
          :can-detach="canDetach"
          @open-gloss="$emit('open-gloss', glossRef(node.gloss))"
          @delete-gloss="handleDelete"
          @toggle-exclude="handleToggleExclude"
          @detach="handleDetach"
        />
      </div>
      <div v-if="isExpanded" class="px-3 pb-3 space-y-2">
        <TreeNodeItem
          v-for="(child, index) in node.children"
          :key="index"
          :node="child"
          :depth="depth + 1"
          @open-gloss="$emit('open-gloss', $event)"
          @delete-gloss="$emit('delete-gloss', $event)"
          @toggle-exclude="$emit('toggle-exclude', $event)"
          @detach="$emit('detach', $event)"
        />
      </div>
    </div>

    <!-- Leaf node - no children -->
    <div v-else class="bg-base-100 shadow rounded-box px-3 py-2 flex items-center gap-2 flex-wrap">
      <NodeContent :node="node" />
      <NodeActions
        :node="node"
        :can-detach="canDetach"
        @open-gloss="$emit('open-gloss', glossRef(node.gloss))"
        @delete-gloss="handleDelete"
        @toggle-exclude="handleToggleExclude"
        @detach="handleDetach"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ChevronRight } from 'lucide-vue-next'
import type { TreeNode } from '../../entities/glosses/treeBuilder'
import NodeContent from './NodeContent.vue'
import NodeActions from './NodeActions.vue'

const props = defineProps<{
  node: TreeNode
  depth: number
}>()

const emit = defineEmits<{
  'open-gloss': [ref: string]
  'delete-gloss': [ref: string]
  'toggle-exclude': [ref: string]
  'detach': [parentRef: string, field: string, childRef: string]
}>()

const hasChildren = computed(() => props.node.children && props.node.children.length > 0)
const isExpanded = ref(false)
const canDetach = computed(() => Boolean(props.node.parentRef && props.node.viaField))

function glossRef(gloss: typeof props.node.gloss): string {
  return `${gloss.language}:${gloss.slug}`
}

function toggleExpanded() {
  isExpanded.value = !isExpanded.value
}

function handleDelete() {
  if (confirm(`Delete gloss "${props.node.display}"? This will clean up all references.`)) {
    emit('delete-gloss', glossRef(props.node.gloss))
  }
}

function handleToggleExclude() {
  emit('toggle-exclude', glossRef(props.node.gloss))
}

function handleDetach() {
  if (!canDetach.value) {
    console.error('Cannot detach: missing parent or relation on node', props.node)
    return
  }
  const parent = props.node.parentRef as string
  const field = props.node.viaField as string
  const child = glossRef(props.node.gloss)
  emit('detach', parent, field, child)
}
</script>

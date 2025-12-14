<template>
  <div :style="{ marginLeft: `${depth * 1.25}rem` }">
    <div class="bg-base-100 shadow rounded-box">
      <div class="flex items-center gap-2 flex-wrap px-3 py-2">
        <NodeContent :node="node" />
        <NodeActions
          :node="node"
          :can-detach="canDetach"
          @open-gloss="$emit('open-gloss', glossRef(node.gloss))"
          @delete-gloss="handleDelete"
          @toggle-exclude="handleToggleExclude"
          @detach="handleDetach"
        />
        <button
          v-if="hasChildren"
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
      </div>
      <div v-if="hasChildren && isExpanded" class="px-3 pb-3 space-y-2">
        <TreeNodeItem
          v-for="(child, index) in node.children"
          :key="index"
          :node="child"
          :depth="depth + 1"
          :expanded-refs="expandedRefs"
          @open-gloss="$emit('open-gloss', $event)"
          @delete-gloss="$emit('delete-gloss', $event)"
          @toggle-exclude="$emit('toggle-exclude', $event)"
          @detach="$emit('detach', $event)"
          @toggle-expand="(ref, expanded) => $emit('toggle-expand', ref, expanded)"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ChevronRight } from 'lucide-vue-next'
import type { TreeNode } from '../../entities/glosses/treeBuilder'
import NodeContent from './NodeContent.vue'
import NodeActions from './NodeActions.vue'

const props = defineProps<{
  node: TreeNode
  depth: number
  expandedRefs?: Record<string, boolean>
}>()

const emit = defineEmits<{
  'open-gloss': [ref: string]
  'delete-gloss': [ref: string]
  'toggle-exclude': [ref: string]
  'detach': [parentRef: string, field: string, childRef: string]
  'toggle-expand': [ref: string, expanded: boolean]
}>()

const hasChildren = computed(() => props.node.children && props.node.children.length > 0)
const isExpanded = computed(() => {
  const ref = glossRef(props.node.gloss)
  return props.expandedRefs ? Boolean(props.expandedRefs[ref]) : false
})
const canDetach = computed(() => Boolean(props.node.parentRef && props.node.viaField))

function glossRef(gloss: typeof props.node.gloss): string {
  return `${gloss.language}:${gloss.slug}`
}

function toggleExpanded() {
  emit('toggle-expand', glossRef(props.node.gloss), !isExpanded.value)
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

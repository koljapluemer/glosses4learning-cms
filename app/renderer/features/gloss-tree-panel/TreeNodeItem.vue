<template>
  <div :style="{ marginLeft: `${depth * 1.25}rem` }">
    <!-- Node with children - collapsible -->
    <div v-if="hasChildren" class="collapse collapse-plus bg-base-100 shadow">
      <input type="checkbox" />
      <div class="collapse-title flex items-center gap-2 flex-wrap">
        <NodeContent :node="node" />
        <NodeActions
          :node="node"
          @open-gloss="$emit('open-gloss', glossRef(node.gloss))"
          @delete-gloss="handleDelete"
          @toggle-exclude="handleToggleExclude"
          @detach="handleDetach"
        />
      </div>
      <div class="collapse-content space-y-2">
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
        @open-gloss="$emit('open-gloss', glossRef(node.gloss))"
        @delete-gloss="handleDelete"
        @toggle-exclude="handleToggleExclude"
        @detach="handleDetach"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
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

function glossRef(gloss: typeof props.node.gloss): string {
  return `${gloss.language}:${gloss.slug}`
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
  const parent = props.node.parentRef
  const field = props.node.viaField
  const child = glossRef(props.node.gloss)
  emit('detach', parent || '', field || '', child)
}
</script>

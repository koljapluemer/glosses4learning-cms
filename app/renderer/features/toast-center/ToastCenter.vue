<template>
  <ToastStack :toasts="toasts" @close="remove" />
</template>

<script setup lang="ts">
import ToastStack from '../../dumb/ToastStack.vue'
import { useToasts } from './useToasts'

const { toasts, remove } = useToasts()
</script>

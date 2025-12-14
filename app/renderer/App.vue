<template>
  <div class="min-h-screen bg-base-100">
    <div class="container mx-auto p-4">
      <RouterView />
    </div>
    <ToastCenter />
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import ToastCenter from './features/toast-center/ToastCenter.vue'
</script>

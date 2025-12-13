<template>
  <div class="min-h-screen bg-base-100">
    <div class="container mx-auto p-4">
      <RouterView />
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

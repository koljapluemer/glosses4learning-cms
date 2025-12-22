<template>
  <div class="min-h-screen bg-base-200">
    <div class="navbar bg-base-100 shadow-lg">
      <div class="flex-1">
        <router-link to="/" class="btn btn-ghost text-xl">
          Glosses4Learning CMS
        </router-link>
      </div>
      <div class="flex-none gap-2">
        <router-link to="/" class="btn btn-ghost">
          Browse Glosses
        </router-link>
      </div>
    </div>

    <div class="container mx-auto p-4">
      <router-view />
    </div>
  </div>
</template>

<script setup lang="ts">
// App component
</script>

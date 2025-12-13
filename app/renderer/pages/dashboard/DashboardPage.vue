<template>
  <div>
    <h1 class="text-3xl font-bold mb-4">Glosses4Learning CMS</h1>

    <div class="card shadow">
      <div class="card-body">
        <h2 class="card-title">Phase 1: Foundation Complete!</h2>
        <p>The basic Electron + Vue + TypeScript + Tailwind + DaisyUI setup is ready.</p>

        <div class="mt-4">
          <button class="btn btn-primary" @click="testIPC">Test IPC</button>
          <p v-if="testResult" class="mt-2">{{ testResult }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const testResult = ref('')

async function testIPC() {
  try {
    const languages = await window.electronAPI.language.list()
    testResult.value = `Loaded ${languages.length} languages: ${languages.map((l: any) => l.displayName).join(', ')}`
  } catch (error) {
    testResult.value = `Error: ${error}`
  }
}
</script>

<template>
  <div class="space-y-4">
    <h1 class="text-3xl font-bold">Browse Glosses</h1>

    <!-- Filters -->
    <div class="card bg-base-100 shadow-xl">
      <div class="card-body">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <!-- Language Selector -->
          <div class="form-control">
            <label class="label">
              <span class="label-text">Language</span>
            </label>
            <select v-model="selectedLanguage" class="select select-bordered w-full">
              <option value="">All Languages</option>
              <option v-for="lang in languages" :key="lang.isoCode" :value="lang.isoCode">
                {{ lang.symbol }} {{ lang.displayName }}
              </option>
            </select>
          </div>

          <!-- Search -->
          <div class="form-control">
            <label class="label">
              <span class="label-text">Search</span>
            </label>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search by content..."
              class="input input-bordered w-full"
              @input="handleSearch"
            />
          </div>

          <!-- Tag Filter -->
          <div class="form-control">
            <label class="label">
              <span class="label-text">Tag Filter</span>
            </label>
            <input
              v-model="tagFilter"
              type="text"
              placeholder="Filter by tag..."
              class="input input-bordered w-full"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex justify-center">
      <span class="loading loading-spinner loading-lg"></span>
    </div>

    <!-- Results -->
    <div v-else-if="glosses.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="gloss in glosses"
        :key="`${gloss.language}:${gloss.slug}`"
        class="card bg-base-100 shadow-xl hover:shadow-2xl transition-shadow cursor-pointer"
        @click="openGloss(gloss)"
      >
        <div class="card-body">
          <h2 class="card-title">{{ gloss.content }}</h2>
          <div class="badge badge-primary">{{ gloss.language }}</div>
          <div class="flex flex-wrap gap-1 mt-2">
            <span v-for="tag in gloss.tags.slice(0, 3)" :key="tag" class="badge badge-sm">
              {{ tag }}
            </span>
            <span v-if="gloss.tags.length > 3" class="badge badge-sm badge-ghost">
              +{{ gloss.tags.length - 3 }}
            </span>
          </div>
          <div class="text-sm text-base-content/60 mt-2">
            {{ gloss.translations.length }} translations • {{ gloss.parts.length }} parts
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="text-center py-12">
      <p class="text-xl text-base-content/60">No glosses found</p>
      <p class="text-sm text-base-content/40 mt-2">Try adjusting your filters</p>
    </div>

    <!-- Pagination Info -->
    <div v-if="glosses.length > 0" class="text-center text-sm text-base-content/60">
      Showing {{ glosses.length }} glosses
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { Gloss } from '@glosses4learning/core'

const router = useRouter()

// State
const languages = ref<Array<{ isoCode: string; displayName: string; symbol: string }>>([])
const selectedLanguage = ref('')
const searchQuery = ref('')
const tagFilter = ref('')
const glosses = ref<Gloss[]>([])
const loading = ref(false)

// Load languages
onMounted(async () => {
  languages.value = await window.electronAPI.language.list()
  loadGlosses()
})

// Watch filters
watch([selectedLanguage, tagFilter], () => {
  loadGlosses()
})

// Debounced search
let searchTimeout: NodeJS.Timeout
function handleSearch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    loadGlosses()
  }, 300)
}

// Load glosses
async function loadGlosses() {
  loading.value = true
  try {
    if (tagFilter.value) {
      // Search by tag
      const results: Gloss[] = []
      for await (const gloss of window.electronAPI.gloss.findByTag(tagFilter.value, 100)) {
        if (!selectedLanguage.value || gloss.language === selectedLanguage.value) {
          results.push(gloss)
        }
      }
      glosses.value = results
    } else if (searchQuery.value && selectedLanguage.value) {
      // Search by content in specific language
      const results: Gloss[] = []
      for await (const gloss of window.electronAPI.gloss.searchByContent(
        selectedLanguage.value,
        searchQuery.value,
        100
      )) {
        results.push(gloss)
      }
      glosses.value = results
    } else {
      // Just show first 100 of selected language (or all languages)
      const results: Gloss[] = []
      if (selectedLanguage.value) {
        // Show glosses from selected language
        let count = 0
        for await (const gloss of window.electronAPI.gloss.findByTag('*', 1000)) {
          if (gloss.language === selectedLanguage.value && count < 100) {
            results.push(gloss)
            count++
          }
        }
      } else {
        // Show first 100 glosses from all languages
        let count = 0
        for await (const gloss of window.electronAPI.gloss.findByTag('*', 1000)) {
          if (count < 100) {
            results.push(gloss)
            count++
          } else {
            break
          }
        }
      }
      glosses.value = results
    }
  } catch (error) {
    console.error('Failed to load glosses:', error)
  } finally {
    loading.value = false
  }
}

function openGloss(gloss: Gloss) {
  router.push({
    name: 'detail',
    params: { language: gloss.language, slug: gloss.slug }
  })
}
</script>

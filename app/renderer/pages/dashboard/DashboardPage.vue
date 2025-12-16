<template>
  <div>
    <h1 class="text-3xl font-bold mb-4">Glosses4Learning CMS</h1>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="card bg-base-200 shadow">
        <div class="card-body">
          <h2 class="card-title">Situations</h2>
          <p class="text-sm text-base-content/70">
            Work on language learning situations and their goals
          </p>
          <div class="card-actions justify-end mt-4">
            <router-link to="/pick-situation" class="btn btn-primary">
              <FolderOpen class="w-4 h-4 mr-2" />
              Open Situation
            </router-link>
          </div>
        </div>
      </div>

      <div class="card bg-base-200 shadow">
        <div class="card-body">
          <h2 class="card-title">Export</h2>
          <p class="text-sm text-base-content/70">
            Export situations and glosses for the learning app
          </p>
          <div class="card-actions justify-end mt-4">
            <button class="btn btn-secondary" :disabled="exporting" @click="exportSituations">
              <Loader2 v-if="exporting" class="w-4 h-4 mr-2 animate-spin" />
              <Download v-else class="w-4 h-4 mr-2" />
              {{ exporting ? 'Exporting...' : 'Export' }}
            </button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { FolderOpen, Download, Loader2 } from 'lucide-vue-next'
import { useSettings } from '../../entities/system/settingsStore'
import { useToasts } from '../../features/toast-center/useToasts'

const router = useRouter()
const route = useRoute()
const exporting = ref(false)
const { settings } = useSettings()
const { error, success, info } = useToasts()

async function exportSituations() {
  if (exporting.value) return
  exporting.value = true
  try {
    const result = await window.electronAPI.situation.export()
    if (!result.success) {
      throw new Error(result.error || 'Export failed')
    }

    const summary = `Exported ${result.totalExports}/${result.totalSituations} situations to ${result.outputRoot}`
    success(summary)

    if (result.skipped.length) {
      info(`Skipped ${result.skipped.length} due to missing learnable content`)
    }
  } catch (err) {
    error(`Export failed: ${err instanceof Error ? err.message : String(err)}`)
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  // Auto-open last situation if available and languages set
  if (route.query.noAutoOpen) {
    return
  }
  const { nativeLanguage, targetLanguage, lastSituationRef } = settings.value
  if (nativeLanguage && targetLanguage && lastSituationRef) {
    const [lang, ...slugParts] = lastSituationRef.split(':')
    const slug = slugParts.join(':')
    if (lang && slug) {
      router.push({
        name: 'situation-workspace',
        params: {
          situationLang: lang,
          situationSlug: slug
        },
        query: {
          native: nativeLanguage,
          target: targetLanguage
        }
      })
    }
  }
})
</script>

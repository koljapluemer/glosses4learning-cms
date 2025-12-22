<template>
  <div v-if="gloss" class="space-y-4">
    <!-- Header -->
    <div class="flex justify-between items-center">
      <button class="btn btn-ghost" @click="$router.back()">
        ← Back
      </button>
      <div class="flex gap-2">
        <button class="btn btn-primary" @click="saveGloss" :disabled="saving">
          {{ saving ? 'Saving...' : 'Save' }}
        </button>
        <button class="btn btn-error" @click="deleteGloss">
          Delete
        </button>
      </div>
    </div>

    <!-- Content Editor -->
    <div class="card bg-base-100 shadow-xl">
      <div class="card-body">
        <h2 class="card-title">Content</h2>
        <input
          v-model="gloss.content"
          type="text"
          class="input input-bordered w-full text-2xl"
          placeholder="Gloss content..."
        />
        <div class="badge badge-primary mt-2">{{ gloss.language }}</div>
      </div>
    </div>

    <!-- Flags -->
    <div class="card bg-base-100 shadow-xl">
      <div class="card-body">
        <h2 class="card-title">Flags</h2>
        <div class="flex gap-4">
          <label class="label cursor-pointer gap-2">
            <input
              v-model="gloss.needsHumanCheck"
              type="checkbox"
              class="checkbox"
            />
            <span class="label-text">Needs Human Check</span>
          </label>
          <label class="label cursor-pointer gap-2">
            <input
              v-model="gloss.excludeFromLearning"
              type="checkbox"
              class="checkbox"
            />
            <span class="label-text">Exclude From Learning</span>
          </label>
        </div>
      </div>
    </div>

    <!-- Transcriptions -->
    <div class="card bg-base-100 shadow-xl">
      <div class="card-body">
        <h2 class="card-title">Transcriptions</h2>
        <div class="space-y-2">
          <div v-for="(value, key) in gloss.transcriptions" :key="key" class="flex gap-2">
            <input
              :value="key"
              type="text"
              class="input input-bordered flex-1"
              placeholder="Type (e.g., IPA)"
              disabled
            />
            <input
              v-model="gloss.transcriptions[key]"
              type="text"
              class="input input-bordered flex-1"
              placeholder="Transcription"
            />
            <button class="btn btn-error btn-square" @click="delete gloss.transcriptions[key]">
              ×
            </button>
          </div>
          <button class="btn btn-sm btn-ghost" @click="addTranscription">
            + Add Transcription
          </button>
        </div>
      </div>
    </div>

    <!-- Relationships (Tabs) -->
    <div class="card bg-base-100 shadow-xl">
      <div class="card-body">
        <h2 class="card-title">Relationships</h2>
        <div class="tabs tabs-boxed">
          <a
            v-for="field in relationshipFields"
            :key="field"
            class="tab"
            :class="{ 'tab-active': selectedTab === field }"
            @click="selectedTab = field"
          >
            {{ formatFieldName(field) }} ({{ (gloss[field] as string[]).length }})
          </a>
        </div>

        <div class="mt-4 space-y-2">
          <div
            v-for="(ref, index) in (gloss[selectedTab] as string[])"
            :key="index"
            class="flex items-center gap-2 p-2 bg-base-200 rounded"
          >
            <span class="flex-1">{{ ref }}</span>
            <button class="btn btn-sm btn-error" @click="removeRelation(selectedTab, ref)">
              Remove
            </button>
          </div>
          <button class="btn btn-sm btn-ghost" @click="addRelation(selectedTab)">
            + Add {{ formatFieldName(selectedTab) }}
          </button>
        </div>
      </div>
    </div>

    <!-- Images -->
    <div class="card bg-base-100 shadow-xl">
      <div class="card-body">
        <h2 class="card-title">Images</h2>
        <div class="tabs tabs-boxed">
          <a
            class="tab"
            :class="{ 'tab-active': imageTab === 'decorative' }"
            @click="imageTab = 'decorative'"
          >
            Decorative ({{ gloss.decorativeImages?.length || 0 }})
          </a>
          <a
            class="tab"
            :class="{ 'tab-active': imageTab === 'semantic' }"
            @click="imageTab = 'semantic'"
          >
            Semantic ({{ gloss.semanticImages?.length || 0 }})
          </a>
          <a
            class="tab"
            :class="{ 'tab-active': imageTab === 'unambiguous' }"
            @click="imageTab = 'unambiguous'"
          >
            Unambiguous ({{ gloss.unambigiousImages?.length || 0 }})
          </a>
        </div>
        <div class="mt-4">
          <div v-if="imageTab === 'decorative'" class="space-y-2">
            <div v-for="(img, index) in gloss.decorativeImages" :key="index">{{ img }}</div>
          </div>
          <div v-if="imageTab === 'semantic'" class="space-y-2">
            <div v-for="(img, index) in gloss.semanticImages" :key="index">{{ img }}</div>
          </div>
          <div v-if="imageTab === 'unambiguous'" class="space-y-2">
            <div v-for="(img, index) in gloss.unambigiousImages" :key="index">{{ img }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div v-else class="text-center py-12">
    <span class="loading loading-spinner loading-lg"></span>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import type { Gloss } from '@glosses4learning/core'

const props = defineProps<{
  language: string
  slug: string
}>()

const router = useRouter()

const gloss = ref<Gloss | null>(null)
const saving = ref(false)
const selectedTab = ref('translations')
const imageTab = ref('decorative')

const relationshipFields = [
  'translations',
  'parts',
  'usage_examples',
  'morphologically_related',
  'has_similar_meaning',
  'sounds_similar',
  'to_be_differentiated_from',
  'collocations',
  'typical_follow_up',
  'children',
  'notes',
  'tags'
]

onMounted(async () => {
  gloss.value = await window.electronAPI.gloss.load(props.language, props.slug)
})

function formatFieldName(field: string): string {
  return field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

async function saveGloss() {
  if (!gloss.value) return
  saving.value = true
  try {
    await window.electronAPI.gloss.save(gloss.value)
    alert('Saved!')
  } catch (error) {
    console.error('Save failed:', error)
    alert('Save failed: ' + error)
  } finally {
    saving.value = false
  }
}

async function deleteGloss() {
  if (!gloss.value) return
  if (!confirm(`Delete "${gloss.value.content}"?`)) return

  try {
    await window.electronAPI.gloss.deleteWithCleanup(gloss.value.language, gloss.value.slug!)
    router.push('/')
  } catch (error) {
    console.error('Delete failed:', error)
    alert('Delete failed: ' + error)
  }
}

function addTranscription() {
  if (!gloss.value) return
  const key = prompt('Transcription type (e.g., IPA):')
  if (key && key.trim()) {
    gloss.value.transcriptions[key.trim()] = ''
  }
}

function addRelation(field: string) {
  if (!gloss.value) return
  const ref = prompt(`Enter reference (e.g., eng:hello):`)
  if (ref && ref.trim()) {
    const relations = gloss.value[field as keyof Gloss] as string[]
    relations.push(ref.trim())
  }
}

function removeRelation(field: string, ref: string) {
  if (!gloss.value) return
  const relations = gloss.value[field as keyof Gloss] as string[]
  const index = relations.indexOf(ref)
  if (index > -1) {
    relations.splice(index, 1)
  }
}
</script>

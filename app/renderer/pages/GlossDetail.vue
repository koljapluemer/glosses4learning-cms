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

    <!-- Audio Pronunciations -->
    <div class="card bg-base-100 shadow-xl">
      <div class="card-body">
        <h2 class="card-title">Audio Pronunciations</h2>

        <!-- Upload Button -->
        <button
          class="btn btn-primary"
          @click="uploadAudio"
          :disabled="uploadingAudio"
        >
          {{ uploadingAudio ? 'Uploading...' : 'Pick & Upload Audio' }}
        </button>

        <!-- Pronunciation List -->
        <div class="space-y-4 mt-4">
          <div
            v-for="(pronunciation, index) in gloss.audioPronunciations"
            :key="pronunciation.filename"
            class="card bg-base-200"
          >
            <div class="card-body p-4">
              <!-- Header Row -->
              <div class="flex justify-between items-start">
                <h3 class="font-semibold">{{ pronunciation.filename }}</h3>
                <button
                  class="btn btn-error btn-sm btn-square"
                  @click="deleteAudioPronunciation(index)"
                >
                  ×
                </button>
              </div>

              <!-- Audio Player -->
              <audio
                controls
                class="w-full mt-2"
                @error="handleAudioError(pronunciation.filename)"
              >
                <source :src="getAudioDataUrl(pronunciation.filename)" type="audio/mpeg">
                Your browser does not support the audio element.
              </audio>

              <!-- Comment Input -->
              <div class="mt-2">
                <label class="label">
                  <span class="label-text">Comment</span>
                </label>
                <textarea
                  v-model="pronunciation.comment"
                  class="textarea textarea-bordered w-full"
                  rows="2"
                  placeholder="Optional comment (e.g., 'Formal pronunciation', 'Regional variant')..."
                />
              </div>
            </div>
          </div>

          <!-- Empty State -->
          <div v-if="!gloss.audioPronunciations?.length" class="text-center py-8 text-base-content/50">
            No audio pronunciations yet. Upload one above!
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
const uploadingAudio = ref(false)
const audioDataCache = ref<Map<string, string>>(new Map())

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

  // Initialize audioPronunciations if undefined
  if (gloss.value && !gloss.value.audioPronunciations) {
    gloss.value.audioPronunciations = []
  }

  // Preload audio data for existing pronunciations
  if (gloss.value?.audioPronunciations) {
    for (const pronunciation of gloss.value.audioPronunciations) {
      await loadAudioData(pronunciation.filename)
    }
  }
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

// Audio pronunciation methods
async function loadAudioData(filename: string): Promise<void> {
  try {
    const base64 = await window.electronAPI.audio.load(filename)
    audioDataCache.value.set(filename, base64)
  } catch (error) {
    console.error(`Failed to load audio: ${filename}`, error)
  }
}

function getAudioDataUrl(filename: string): string {
  const base64 = audioDataCache.value.get(filename)
  return base64 ? `data:audio/mpeg;base64,${base64}` : ''
}

async function uploadAudio() {
  if (!gloss.value) return

  uploadingAudio.value = true
  try {
    // Pick file via dialog
    const base64Data = await window.electronAPI.audio.pickFile()
    if (!base64Data) {
      uploadingAudio.value = false
      return // User cancelled
    }

    // Calculate next index
    const nextIndex = gloss.value.audioPronunciations?.length || 0

    // Upload and process
    const filename = await window.electronAPI.audio.upload(
      base64Data,
      gloss.value.slug!,
      nextIndex
    )

    // Add to gloss
    if (!gloss.value.audioPronunciations) {
      gloss.value.audioPronunciations = []
    }
    gloss.value.audioPronunciations.push({
      filename,
      comment: ''
    })

    // Cache audio data
    audioDataCache.value.set(filename, base64Data)

    alert(`Audio uploaded successfully: ${filename}`)
  } catch (error) {
    console.error('Upload failed:', error)
    alert('Upload failed: ' + error)
  } finally {
    uploadingAudio.value = false
  }
}

async function deleteAudioPronunciation(index: number) {
  if (!gloss.value?.audioPronunciations) return

  const pronunciation = gloss.value.audioPronunciations[index]
  if (!confirm(`Delete "${pronunciation.filename}"?`)) return

  try {
    // Delete file from storage
    await window.electronAPI.audio.delete(pronunciation.filename)

    // Remove from gloss
    gloss.value.audioPronunciations.splice(index, 1)

    // Clear cache
    audioDataCache.value.delete(pronunciation.filename)

    alert('Audio deleted successfully')
  } catch (error) {
    console.error('Delete failed:', error)
    alert('Delete failed: ' + error)
  }
}

function handleAudioError(filename: string) {
  console.error(`Audio playback error: ${filename}`)
  alert(`Failed to play audio: ${filename}. The file may be corrupted.`)
}
</script>

# Implementation Plan: Glosses4Learning Electron App

Complete implementation of electron_spec.md with exact ports from Python codebase.

---

## PHASE 0: CRITICAL BUG FIX - Language Selection [PRIORITY]

**Problem**: Can open situations without native/target languages → breaks goal evaluation, AI tools, tree rendering.

**Spec**: electron_spec.md:8-11

### Files to CREATE:

**1. `app/renderer/entities/languages/types.ts`** ✅
```typescript
export interface Language {
  isoCode: string      // ISO 639-3
  displayName: string
  symbol: string       // e.g., 'EN' or '🇲🇽'
  aiNote?: string
}
```
**Python ref**: `src/schema/language.schema.json`

**2. `app/renderer/entities/languages/loader.ts`** ✅
- `loadLanguages()` → Language[] (cached)
- `getLanguageSymbol(isoCode, languages)` → string
**Python ref**: `src/shared/languages.py:11-25`

**3. `app/renderer/entities/system/settingsStore.ts`**
- Vue composable for native/target language state
- Persists to electron-store via IPC
- `useSettings()` returns reactive settings + setters
**Python ref**: `src/shared/state.py:8-32`

### Files to MODIFY:

**4. `app/renderer/features/situation-picker/SituationPicker.vue`**

Add at top:
```vue
<div class="grid grid-cols-2 gap-4 mb-6 pb-4 border-b">
  <fieldset class="fieldset">
    <label class="label">Native Language</label>
    <select v-model="localNative" class="select select-bordered w-full">
      <option v-for="lang in languages" :value="lang.isoCode">
        {{ lang.symbol }} {{ lang.displayName }}
      </option>
    </select>
  </fieldset>
  <!-- Same for Target Language -->
</div>
```

Add action buttons per situation:
- Delete button → `window.electronAPI.gloss.deleteWithCleanup()`
- Unsituate button → Remove "eng:situation" tag
- Edit button → Open gloss modal (Phase 6)

Block selection until both languages set.

**Python refs**:
- Delete: `src/shared/gloss_actions.py:44-66`
- Tag management: `src/shared/storage.py`

**5. `app/renderer/router.ts`**

Change route from:
```typescript
path: '/situation/:language/:slug'
```
To:
```typescript
path: '/situation/:situationLang/:situationSlug/:nativeLang/:targetLang'
```

**6. `app/renderer/pages/situation-workspace/SituationWorkspace.vue`**

Add top-left button:
```vue
<button class="btn btn-sm" @click="showSituationPicker = true">
  {{ situation.content }} {{ nativeSymbol }}→{{ targetSymbol }}
</button>
```

**7. `app/renderer/main.ts`**

Initialize settings on boot:
```typescript
import { initSettings } from './entities/system/settingsStore'
await initSettings()
app.mount('#app')
```

---

## PHASE 1: Core Storage Infrastructure

**Spec**: electron_spec.md:92-97, 194-196

### Files to FIX:

**1. `app/main-process/storage/slug.ts`**

**CRITICAL**: Must exactly match Python `src/shared/storage.py:61-77`

Fix regex pattern (current differs from Python):
```typescript
// Remove illegal chars: / \ ? * : | " < >
slug = slug.replace(/[/\\?*|":<>]/g, '')
// Remove control chars
slug = slug.replace(/[\x00-\x1F]/g, '')
// Trim trailing spaces/dots (Windows)
slug = slug.replace(/[ .]+$/g, '')
// Truncate to 120 chars, then re-trim
if (slug.length > 120) {
  slug = slug.substring(0, 120).replace(/[ .]+$/g, '')
}
```

**2. `app/main-process/storage/fsGlossStorage.ts`**

**CRITICAL ISSUE**: Current `listGlosses()` loads ALL glosses into memory (violates spec:94).

Add lazy iteration methods:
```typescript
*iterateGlossesByLanguage(language: string): Generator<Gloss>
*iterateAllGlosses(): Generator<Gloss>
*findGlossesByTag(tagRef: string): Generator<Gloss>
*searchGlossesByContent(language: string, substring: string): Generator<Gloss>
```

Add delete with cleanup:
```typescript
deleteGlossWithCleanup(language: string, slug: string): {
  success: boolean
  message: string
  refsRemoved: number
}
```
**Python ref**: `src/shared/gloss_actions.py:19-66`

Algorithm:
1. Delete gloss file
2. Lazy iterate ALL glosses
3. For each gloss, check ALL 12 relationship fields
4. Remove references to deleted gloss
5. Save modified glosses
6. Return count

**3. `app/main-process/ipc/glossHandlers.ts`**

**CRITICAL FIX**: `gloss:checkReferences` currently loads all glosses.

Rewrite to use lazy iteration:
```typescript
ipcMain.handle('gloss:checkReferences', async (_, ref: string) => {
  const usage = { usedAsPart: [], usedAsUsageExample: [], usedAsTranslation: [] }
  for (const gloss of storage.iterateAllGlosses()) {
    if (gloss.parts?.includes(ref)) usage.usedAsPart.push(...)
    // etc
  }
  return usage
})
```

Add new handlers:
- `gloss:deleteWithCleanup`
- `gloss:findByTag` (with limit param)
- `gloss:searchByContent` (with limit param)
- `gloss:attachTranslationWithNote`
- `gloss:markLog`

### Files to CREATE:

**4. `app/main-process/storage/glossOperations.ts`**

Helper utilities:
- `attachTranslationWithNote()` - creates translation + note gloss
- `markGlossLog()` - adds timestamped log entry

**Python ref**: `src/shared/gloss_operations.py:10-104`

**5. Update `app/preload.ts`**

Add new IPC methods to API surface.

---

## PHASE 2: Tree Building & Goal State Evaluation

**Spec**: electron_spec.md:30, 43-48

### Files to CREATE:

**1. `app/renderer/entities/glosses/goalState.ts`**

Port exact algorithms from `src/shared/tree.py:12-223`:

```typescript
export function detectGoalType(
  gloss: Gloss,
  nativeLang: string,
  targetLang: string
): 'procedural' | 'understanding' | null {
  if (gloss.language === nativeLang &&
      gloss.tags.includes('eng:procedural-paraphrase-expression-goal')) {
    return 'procedural'
  }
  if (gloss.language === targetLang &&
      gloss.tags.includes('eng:understand-expression-goal')) {
    return 'understanding'
  }
  return null
}

export function evaluateGoalState(
  gloss: Gloss,
  storage: GlossStorage,
  nativeLang: string,
  targetLang: string
): { state: 'red' | 'yellow' | 'green', log: string[] }
```

**Understanding goals (tree.py:108-161)**:
- RED if: no target expression, no parts, no native translations
- YELLOW if: has parts + native translations on parts
- GREEN if: ≥2 native translations + parts have ≥2 usage examples

**Procedural goals (tree.py:163-207)**:
- RED if: no native expression, no target translations
- YELLOW if: has target translations with parts + back-translations
- GREEN if: ≥2 target translations

Helper functions:
```typescript
export function paraphraseDisplay(gloss: Gloss): string {
  // Wrap in [brackets] if tagged 'eng:paraphrase'
}
```
**Python ref**: `src/shared/tree.py:225-231`

**2. `app/renderer/entities/glosses/treeBuilder.ts`**

Port exact algorithm from `src/shared/tree.py:234-428`:

```typescript
export function buildGoalNodes(
  situation: Gloss,
  storage: GlossStorage,
  nativeLang: string,
  targetLang: string
): { nodes: TreeNode[], stats: TreeStats }
```

Algorithm:
1. Initialize stats (situationGlosses, glossesToLearn, warning sets)
2. Define recursive `buildNode()` function
3. For each goal in situation.children:
   - Detect type (procedural vs understanding)
   - Build node tree with cycle detection
   - Expand parts, translations, usage examples based on type
   - Track warnings (native_missing, target_missing, parts_missing, usage_missing)
4. Return nodes + stats

**Critical edge cases**:
- Procedural goals skip their own parts (line 333)
- Target-language paraphrases excluded (line 294)
- Usage lineage flag prevents recursion (line 378)
- Respect log markers: SPLIT_CONSIDERED_UNNECESSARY, TRANSLATION_CONSIDERED_IMPOSSIBLE, etc.

**3. `app/renderer/features/gloss-tree-panel/GlossTreePanel.vue`**

Tree rendering component with:
- Recursive TreeNode display
- State badges (RED/YELLOW/GREEN) on root
- Goal type markers (PROC/UNDR)
- Warning icons per node
- Per-node actions:
  - Delete (with cleanup)
  - Toggle exclude_from_learning
  - Detach from parent (smart field detection)
  - Open gloss modal
- Paraphrase wrapping in [brackets]
- Collapsible nodes

**Python ref**: `src/flask/tree/show_tree.html:1-150`

**Design**: Follow how_to_design.md - lean, Tailwind+DaisyUI, clean layouts

---

## PHASE 3: Overview Tab & Goal Management

**Spec**: electron_spec.md:23-40

### Files to CREATE/MODIFY:

**1. `app/renderer/pages/situation-workspace/OverviewTab.vue`**

**Goals table** (spec:24-30):
- Columns: Content, Type, State (badge), Actions
- Load goals from situation.children
- Evaluate state using `evaluateGoalState()`
- Actions: Open tab, Disattach, Delete, Edit

**Manual goal addition** (spec:31-34):
- Input for procedural goals (native lang, tag: eng:procedural-paraphrase-expression-goal)
- Input for understanding goals (target lang, tag: eng:understand-expression-goal)
- Auto-attach to situation as child

**Python refs**:
- `agent/tools/database/add_gloss_procedural.py:25-42`
- `agent/tools/database/add_gloss_understanding.py:25-42`

**AI tools** (spec:35-40):
- "Add Understand Goals" button
- "Add Procedural Goals" button
- Modal to confirm/reject each generated goal (pre-select all)

**Python refs**:
- `agent/tools/database/generate_understanding_goals.py:13-59` (temp 0.7)
- `agent/tools/database/generate_procedural_goals.py:13-67` (temp 0.7)

---

## PHASE 4: Gloss Modal - Complete CRUD

**Spec**: electron_spec.md:56-87

### Files to CREATE:

**1. `app/renderer/features/gloss-modal/GlossModal.vue`**

**Structure**:
- Language locked (display only)
- No explicit save button (all changes live)
- Toast notifications for all actions

**Content editing** (spec:59-65):
- Edit on blur
- Pre-change check: scan all glosses for usage in parts/usageExamples/translations
- Confirmation modal if used elsewhere
**Python ref**: `src/flask/gloss-crud/app.py:116-183`

**Translations** (spec:66-72):
- Display existing (delete/disattach buttons)
- Inline input with autocomplete (language auto-set to "the other")
- AI generation button → modal with proposals (pre-selected)
- Untranslatable toggle (log: TRANSLATION_CONSIDERED_IMPOSSIBLE:{lang})
**Python refs**:
- Regular: `agent/tools/llm/translate_native_glosses.py:8-24` (temp 0.2)
- Paraphrased: `agent/tools/llm/translate_paraphrased_native.py:8-34` (temp 0.2)

**Parts** (spec:73): Same pattern as translations
- AI: `agent/tools/maintenance/fix_missing_parts.py:94-132`
- Unsplittable toggle (log: SPLIT_CONSIDERED_UNNECESSARY)

**Usage Examples** (spec:74): Same pattern
- AI: `agent/tools/maintenance/fix_usage_examples.py:85-124`
- Toggle (log: USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE)

**Children** (spec:75): Display + inline input (no AI, no toggle)

**Notes** (spec:76-77):
- Tabular view (lang dropdown + content)
- Default lang: native
- Special delete check: if note used elsewhere, only disattach

**Transcriptions** (spec:78-81):
- Tabular dict editor (type + transcription)
- Last row always empty to add new

**Flags** (spec:82-83):
- Toggle excludeFromLearning
- Toggle needsHumanCheck

**Delete** (spec:84-85):
- Check relationships across all glosses
- Confirmation modal with usage list
- Call deleteGlossWithCleanup

---

## PHASE 5: AI Tools Integration

**Spec**: electron_spec.md:49-55, 111

### Setup:

**1. Install OpenAI Agents SDK**
```bash
npm install openai-agents-js
```

**2. API Key Storage**
- Use electron-store (settingsStore.ts)

### Files to CREATE:

**3. `app/renderer/features/ai-batch-tools/AiBatchToolPanel.vue`**

**Three maintenance flows**:

**Fix Missing Translations** (spec:52):
- Port `agent/tools/maintenance/fix_missing_translations.py:46-187`
- Categorize into 3 groups:
  1. Native glosses → target translations
  2. Target glosses → native translations
  3. Paraphrased native → real target expressions (**CRITICAL**: use translate_paraphrased_native.py)
- Batch size: 25
- Modal with pre-selected proposals

**Fix Missing Parts** (spec:54):
- Port `agent/tools/maintenance/fix_missing_parts.py:50-176`
- Check splittability first (temp 0.0, batch 20)
- Generate parts (temp 0.2)
- Modal with proposals

**Fix Missing Usage Examples** (spec:50):
- Port `agent/tools/maintenance/fix_usage_examples.py:51-165`
- Check suitability (temp 0.0, batch 20)
- Generate examples (temp 0.2)
- Modal with proposals

### OpenAI Agents:

Create wrappers for:
1. `generate_understanding_goals` (temp 0.7)
2. `generate_procedural_goals` (temp 0.7)
3. `translate_glosses` (temp 0.2)
4. `translate_paraphrased` (temp 0.2) - **CRITICAL**: find real expressions
5. `check_splittability` (temp 0.0)
6. `generate_parts` (temp 0.2)
7. `check_usage_suitability` (temp 0.0)
8. `generate_usage_examples` (temp 0.2)

Port exact prompts from Python files.

---

## PHASE 6: Code Quality & Architecture

**Spec**: electron_spec.md:103-126, how_to_design.md

### Tasks:

**1. ESLint Setup**
```bash
npm install -D eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin eslint-plugin-vue
```

Fix all issues - NO disabling rules (spec:112)

**2. Architecture Validation**

Verify Feature-Sliced Design (spec:119-124):
- `app/` - minimal, only global stuff
- `dumb/` - no business logic, no high-level imports
- `entities/` - models + storage only
- `features/` - NO cross-feature imports
- `meta/` - only imports from below
- `pages/` - page-specific code only

No `index.ts` reexports (spec:126)

**3. Design Principles** (how_to_design.md)

- Lean design - minimal wrappers/containers
- Tailwind + DaisyUI
- Standard buttons, consistent spacing (1, 2, 4, 6)
- Clean grid/flex layouts
- Short copy, no marketing speak
- Mobile + desktop responsive

---

## Critical Implementation Notes

### Must Preserve Python Behavior:

1. **Slug generation** (spec:96): EXACTLY match Python - illegal char removal, 120 truncation, Unicode preservation
2. **Symmetrical relationships**: translations, morphologically_related, has_similar_meaning, sounds_similar, to_be_differentiated_from
3. **Relationship cleanup**: Scan ALL 12 fields across ALL languages on delete
4. **Log markers**: Respect SPLIT_CONSIDERED_UNNECESSARY, TRANSLATION_CONSIDERED_IMPOSSIBLE, etc.
5. **Paraphrased translations**: Find real expressions, not literal (translate_paraphrased_native.py)
6. **Temperature settings**: 0.7 creative, 0.2 translation, 0.0 judgment
7. **Batching**: 25 for translations, 20 for parts/usage
8. **Pre-selection**: All confirmation modals pre-select all items (spec:98)
9. **Paraphrase rendering**: Wrap in [brackets] (spec:95)
10. **Memory management**: NEVER load all glosses - use lazy iteration (spec:94)

### Python Reference Map:

| Component | Python Files |
|-----------|--------------|
| Slug | `src/shared/storage.py:61-77` |
| Storage | `src/shared/storage.py:149-481` |
| Relations | `src/shared/storage.py:14-54`, `src/flask/gloss-crud/relations.py` |
| Delete cleanup | `src/shared/gloss_actions.py:44-95` |
| Goal type | `src/shared/tree.py:12-22` |
| Goal state | `src/shared/tree.py:25-223`, `doc/reference_what_is_a_valid_goal.md` |
| Tree building | `src/shared/tree.py:234-406` |
| Languages | `src/shared/languages.py:13-52` |
| AI translations | `agent/tools/llm/translate_*.py` |
| AI maintenance | `agent/tools/maintenance/fix_*.py` |
| AI generation | `agent/tools/database/generate_*.py` |

---

## Implementation Order

1. **Phase 0** - Language selection (fixes critical bug)
2. **Phase 1** - Core storage (lazy iteration, cleanup)
3. **Phase 2** - Tree & goal state (evaluation logic)
4. **Phase 3** - Overview tab (goal management)
5. **Phase 4** - Gloss modal (complete CRUD)
6. **Phase 5** - AI tools (OpenAI SDK integration)
7. **Phase 6** - Code quality (ESLint, architecture)

Each phase builds on previous, maintaining working state throughout.

---

## Key Files Summary

**CREATE** (18 new files):
- `app/renderer/entities/languages/types.ts` ✅
- `app/renderer/entities/languages/loader.ts` ✅
- `app/renderer/entities/system/settingsStore.ts`
- `app/renderer/entities/glosses/goalState.ts`
- `app/renderer/entities/glosses/treeBuilder.ts`
- `app/renderer/features/gloss-tree-panel/GlossTreePanel.vue`
- `app/renderer/pages/situation-workspace/OverviewTab.vue`
- `app/renderer/features/gloss-modal/GlossModal.vue`
- `app/renderer/features/ai-batch-tools/AiBatchToolPanel.vue`
- `app/main-process/storage/glossOperations.ts`
- (+ supporting composables, types, utilities)

**MODIFY** (10 existing files):
- `app/renderer/features/situation-picker/SituationPicker.vue` - Add language dropdowns
- `app/renderer/router.ts` - Update route signature
- `app/renderer/pages/dashboard/DashboardPage.vue` - Pass languages
- `app/renderer/pages/situation-workspace/SituationWorkspace.vue` - Add top button
- `app/renderer/main.ts` - Initialize settings
- `app/main-process/storage/slug.ts` - Fix regex
- `app/main-process/storage/fsGlossStorage.ts` - Add lazy iteration
- `app/main-process/ipc/glossHandlers.ts` - Fix memory issues, add handlers
- `app/preload.ts` - Extend API surface
- `eslint.config.js` - Setup linting

---

This plan covers all 224 lines of electron_spec.md with exact Python codebase references for every requirement.

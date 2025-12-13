Let's unify the various interaction modalities into a single, coherent, electron+vue+ts+tailwind+daisy app.

Should live in `app/` and be written in JS, so no dependencies on any python code ofc.


## General UI

- at the top-left, we have a button which displays current situation and selected langs (e.g. "at the airport eng→spa").
    - when clicked, opens daisy modal where we 
        - two dropdowns to set native and target lang
            - languages source of truth should still be [this](src/schema/language.schema.json) 
        - have a list of situations, filterable with substring matching with a input box on top
            - clicking the list `content` itself makes the situation the active situation
            - icon button to delete the situation
            - icon button to make the gloss not a situation (removes "eng:situation" from `tags` of the gloss)
            - icon button to open the gloss modal for the situation
        - below the list have an input field to add new situations
            - after adding a new one, input field is spawned again automatically
            - note: situations glosses are always in english
                - this fact does not need to be EXPLAINED in the UI, simply considered in the logic
- below that, we have a tabbed view, using vue router under the hood
    - tabs should show up in a left sidebar
    - the first tab should always be "Overview"
        - it should list all valid goals attached to this situation in a simple table
            - clicking on a goal opens the relevant tab
            - icon button for disattaching this goal from this situation
            - icon button for deleting the goal gloss (and of course, thanks to the relationship clear-up function, also detech the now dangling gloss ref)
                - btw we need a toast system for stuff like "goal x deleted"
            - icon button for editing the gloss data itself as a modal (modal description follows)
            - show goal implicit state "RED" "YELLOW" "GREEN"
        - below the list, we should have input fields to manually add goals
            - one for `procedural-paraphrase-expression-goal`s, always in the set native lang
                - make sure on creation its attached to the situation, and tagged with `eng:procedural-paraphrase-expression-goal`
            - one for `understand-expression-goal`, always in target lang, working similarly
        - below that, some AI tools. For now, only:
            - "Add Understand Goals", with optional text input for context, number input for how many.
                - AI runs, then modal to confirm/reject each of the generated goal
            - "Add Proceduaral Paraphrase Expression Goals"
                - same schema
                - make sure that all tags and relations are set correctly when confirming
    - the tabs below that are for each of the goals attached to the situation, sorted first by type then alphabetically. 
        - 1 goal = 1 tab.
        - each of the tabs should render [the tree](src/flask/tree/show_tree.html), but of course, only for this goal (goal is the root note)
            - additionally to the resolve logic, the warning logic and all the other stuff we already have, allow for each gloss via an icon button:
                - deletion
                - mark as to exclude from Learning (here the button is a sort of toggle, changing state when clicked so it's also indicator)
                - disattach from parent (smartly understand whether it's attached as a part, translation or usage example)
                - open gloss modal
        - below the tree, show AI generation tools
            - "search for and add missing usage examples" corresponding logically exactly to this smart flow: `agent/tools/maintenance/fix_usage_examples.py`
                - show modal at the very end with structured checklist for the user to reject/confirm generations
            - "search for and add missing translations" corresponding logically exactly to this smart flow: `agent/tools/maintenance/fix_missing_translations.py`
                - same modal
            - "search for missing parts and split" corresponding logically exactly to this smart flow: `agent/tools/maintenance/fix_missing_parts.py`
                - same modal
- gloss modal (triggerable via various buttons in the UI described above)
    - we can be inspired by [the existing gloss CRUD here](src/flask/gloss-crud), but we really only need certain features:
        - language is locked and should only be displayed
        - change `content` (make sure to correctly adapt references across codebase if this is done)
            - apply change on blur
                - however, before applying the change, check the following:
                    - is this gloss used in `parts` of another gloss?
                    - is this gloss used in `usageExamples` elsewhere?
                    - is this gloss used in `translations` elsewhere?
                    - if so, open a modal like "you are trying to change 'apple' to 'banana'. However, banana is used as ... in ... (bullet list).", letting the user confirm/reject the change
        - manage translations (display existing, allow delete/disattach, add more via input field, language automatically set to "the other selected")
            - when adding a new one via the input field, automatically string search the gloss data for possible fits and show these autocomplete suggestions
        - add translations via AI
            - optional `<input>` for context and next to that button to run LLM
            - when LLM has run, open modal with the proposals (per default all selected), allow user to accept/reject each via checkbox and confirm, then attach correctly
                - remember that `translations` is a symmetrical relationship
        - toggle to set as untranslatable (works via `logs`, remember to log *into which language* its untranslatable), toggle should be hidden if translations already exist
        - the exact same for `parts`: manage existing, add via smart inline input, AI flow, unsplittable toggle
        - the exact same triplet again for `usageExamples`
        - similar setup for `children`, only just manage existing and adding new via inline input (no AI no toggle)
        - smart editing for notes; tabular view of existing notes, one row for adding a new one (lang select defaulting to the generally selected native language, but open to set + `content`)
            - special here: if a gloss in this `notes` list is also in another `notes` list of another gloss, it cannot be deleted, only disattached (check this on delete attempt, otherwise to expensive)
        - editing for transcriptions, which is as you can [see](src/schema/gloss.schema.json) is a dict
            - tabular view of all existing transcriptions (editable)
                - each row should be a small "transcription type" field and a wider "transcription" field
                - last row always empty, to add a new one if wanted 
        - toggle `excludeFromLearning`
        - toggle `needsHumanCheck`
        - delete
            - similar check for relationships as done when editing `content`
        - clearly communicate via toasts what has been done
        - require no explicit save button for the whole modal, since all the relationship edits are "live" anyways


## General

- we should still use `data/` and `situations/` (via git submodules) as source of truth
- when referencing a gloss, just render its `content` (not its identifier, and not its language unless specified in the spec)
- we may eventually have LITERALLY millions and millions of glosses and thousands of situations. Do NOT load more of them into memory then absolutely necessary. Do NOT add vue global storage layers etc, always interact with a thin layer over the actual `json` gloss files on disk!
- gloss `content` when the gloss has a `tags` entry "eng:paraphrase" should as a rule be rendered wrapped in [ ], hold this consistent
- gloss "slug" generation is EXTREMELY CRITICAL code which should, like it is now, only remove truly illegal filename characters and truncate to a safe length. It should only be defined once.
- when adding or generating a gloss, there is always a chance that this gloss (as identified by the identifier in the form of `$iso_code:$slugified_content` already exist). In that case, code should NOT fail, but simply work with the existing gloss and update relationships accordingly (unless specified differently) 
- on AI suggestion confirm/reject list dialogs, as a rule, pre-select all items
- Generall, A LOT OF THIS LOGIC IS ALREADY IMPLEMENTED IN THIS CODE BASE (only in python) AND ALSO BESPOKE!! Glosses and their relationships and specific LLM tools are used and meant to be used in VERY SPECIFIC WAYS which cannot necessarily be reverse engineered by looking at their descriptors. Make sure to THOROUGHLY understand the existing state and ALWAYS SEARCH FOR relevant inspiration before building.
- This is an INTERNAL EXPERT APP. The users are deeply involved into both the tech and the domain. Therefore, refrain strictly from overexplanation, cutesy messages, bragging about the awesomeness of features, extra labels and descriptive text as well as marketing speak OF ANY KIND.


- Keep design lean. Use cards, wrapper divs and containers ONLY when necessary
- Keep style consistent across the code base
- Setup eslint and ensure green linter (not by disabling it, but by writing clean code)
- Keep files, functions and classes short, with a single purpose, on one abstraction layer. Split complex functionality when called for.
- Do not hallucinate features I did not ask for

- NO PYTHON! Implement as clean TS!!!!!!!! app (no subprocess hacking memes etc.)

- Use openai agents sdk: https://github.com/openai/openai-agents-js (yes, ACTUALLY UTILIZE THIS REAL LIBRARY. not possibly later, no, in this implementation use this actual sdk.)
- WRITE CLEAN CODE!!!!! Linting issues are to be fixed by fixing the fucking issues, not by disabling the linter!!

## Architecture

Do NOT!! adhere to the classic folder-by-type architecture Vue comes with.
Instead, use the following folder structure (inspired by Feature-Sliced Design)

- `app`: Stuff that MUST be global, e.g. the vue boilerplate holding the router view. Can import from anywhere, if it must. Should contain little logic.
- `dumb`: collection of simple, reusable stuff. no business logic. may not import from ANY other high-level folder. may cross-import within the folder. put assets here (if needed)
- `entities`: models/entities. Should contain (global) store.
- `features`: ways of interacting with entities. one folder per feature. may NOT import one another. may ONLY import from `dumb` or `entities`.
- `meta`: for complex features interacting in turn with multiple `features`. One folder per meta-feature. May only import from below, and not from other meta-features. Name features CLEARLY and DESCRIPTIVELY (instead of short and confusing) with full noun and full verb action.
- `pages`: One folder per page (a page is something used by the `router.ts` file). If functionality is ONLY used on a given page, put it in the page folder, do not create features or meta-features that are only used by one single page.

Do not use `index.ts` file reexporting components, simply export directly.

## Specifically needed components

Proposed tree:
```
app/
  main.ts                 # electron main; ipc + file access sandboxing
  preload.ts              # expose limited fs/api surface to renderer
  router.ts               # Vue router with Overview + goal tabs
  tailwind.css
dumb/
  components/ModalShell.vue
  components/TabRail.vue
  components/ToastStack.vue
  components/TreeRow.vue
  components/InlineAddField.vue
entities/
  glosses/
    types.ts
    slug.ts
    fsGlossStorage.ts
    relationRules.ts
    referenceCheck.ts
    treeBuilder.ts
    goalState.ts
  languages/
    loader.ts
    symbols.ts
  situations/
    finder.ts
    recentState.ts
  system/
    ipcClient.ts
    settingsStore.ts
features/
  situation-picker/
    SituationPicker.vue
    useSituationPicker.ts
  goal-overview-table/
    GoalOverviewTable.vue
    useGoalOverviewActions.ts
  goal-tab-frame/
    GoalTabFrame.vue
    useGoalRouting.ts
  gloss-tree-panel/
    GlossTreePanel.vue
    useTreeInteractions.ts
  gloss-modal/
    GlossModal.vue
    useGlossEdits.ts
  ai-batch-tools/
    AiBatchToolPanel.vue
    useAiGeneration.ts
  toast-center/
    ToastCenter.vue
    useToasts.ts
meta/
  situation-workspace/
    SituationWorkspace.vue
    useWorkspaceLoader.ts
pages/
  dashboard/
    DashboardPage.vue
    useDashboardData.ts
```

Component logic + considerations + open questions:
- `app/main.ts` + `preload.ts`: constrain fs access to `data/` + `situations/`, stream reads/writes instead of bulk loading; mirror `src/shared/storage.py` behaviour for path layout. Open question: do we need background worker for long AI runs vs blocking renderer? *as simple as possible right now, we will optimize/async/nonblock when it actually becomes a problem*
- `entities/glosses/slug.ts`: exact port of `derive_slug` from `src/shared/storage.py` (illegal char stripping, truncation) to avoid regressions. Critical that only one slug generator exists.
- `entities/glosses/fsGlossStorage.ts`: JS analogue of `GlossStorage` with `resolve_reference`, `ensure_gloss`, `create_gloss`, `save_gloss`, symmetric attach per `relationRules` (copy `RELATIONSHIP_FIELDS`, `WITHIN_LANGUAGE_RELATIONS`, `SYMMETRICAL_RELATIONS`). Use lazy file reads and per-language iterators to avoid loading millions of glosses at once. Inspiration: `src/shared/storage.py`, `src/flask/gloss-crud/relations.py`.
- `entities/glosses/referenceCheck.ts`: helper for “content change” confirmation modal (scan usages in `parts`, `usage_examples`, `translations`) akin to `_update_references` in `src/flask/gloss-crud/app.py`.
- `entities/glosses/treeBuilder.ts` + `goalState.ts`: port of `build_goal_nodes`, `render_tree_text`, and `evaluate_goal_state` from `src/shared/tree.py` to drive tree rendering + RED/YELLOW/GREEN badges and warnings. Keep same markers (`SPLIT_CONSIDERED_UNNECESSARY`, `TRANSLATION_CONSIDERED_IMPOSSIBLE`, `USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE`).
- `entities/languages/loader.ts`: read from `data/language/*.json`; reuse shape from `src/schema/language.schema.json`. Needed for dropdowns + symbols. Inspiration: `src/shared/languages.py`.
- `entities/situations/finder.ts`: stream situations tagged `eng:situation`, provide substring filter + creation. Reuse attach logic from `agent/tools/database/attach_to_situation.py` + goal adders. Ensure new situations default to English language.
- `features/situation-picker`: modal for language switch + situation list/add/delete; uses `finder.ts` and `fsGlossStorage` attach/detach; confirm delete with cleanup mirroring `src/shared/gloss_actions.delete_gloss_with_cleanup`.
- `features/goal-overview-table`: table of goals with detach/delete/edit actions, badges for state; uses `goalState.ts`; triggers `gloss-modal` for edits. Should call storage detach mirroring `relations.detach_relation`. Inspiration: `src/flask/situation-goals/app.py` and `agent/tools/database/add_gloss_*`.
- `features/goal-tab-frame`: drives router tab labels/order; ensures first tab is Overview and others sorted by type/name.
- `features/gloss-tree-panel`: renders per-goal tree; use `treeBuilder` results; per-node actions (delete, exclude, detach, open modal). Use virtualization for huge trees and guard against cycles. Inspiration: `src/flask/tree/show_tree.html`.
- `features/gloss-modal`: CRUD for translations/parts/usages/notes/children/flags with live saves; run pre-change usage checks via `referenceCheck`; autocomplete by streaming `fsGlossStorage` search per language; enforce symmetry and within-language constraints; warn before delete using `gloss_actions.delete_gloss_with_cleanup`. AI buttons hand off to `ai-batch-tools`.
- `features/ai-batch-tools`: UI for “Add Understand Goals”, “Add Procedural...”, missing translations/parts/usages flows; orchestrates proposal modals with preselected items and confirmation. Logic mirrors `agent/tools/maintenance/fix_*`, `agent/tools/database/add_*`, and `src/shared/gloss_actions.py` LLM helpers (parts/translations/usages). Open question: invoke existing python flows via subprocess vs JS reimplementation of prompts. *No python ANYWHERE!!!!!!!!!! js implementation!
- `features/toast-center`: central toast queue for success/error from storage + AI actions; keep minimal global state.
- `meta/situation-workspace`: composes picker, overview, goal tabs, tree, AI tools into layout described in spec; keeps only current situation/goals in memory, fetches glosses on-demand. Uses `recentState` to persist last choice (similar to `src/shared/state.py`).
- `pages/dashboard`: top-level page (router target) wiring workspace + toasts; no extra business logic.

Existing inspiration to lean on:
- Relationship + slug rules: `src/shared/storage.py`, `src/flask/gloss-crud/relations.py`, `src/shared/gloss_operations.py`.
- Goal state + tree rendering: `src/shared/tree.py`, `src/flask/tree/show_tree.html`.
- Goal creation and maintenance flows: `agent/tools/database/add_gloss_procedural.py`, `agent/tools/database/add_gloss_understanding.py`, `agent/tools/maintenance/fix_missing_translations.py`, `fix_usage_examples.py`, `fix_missing_parts.py`.
- CRUD edge cases (rename/update refs, delete cleanup): `src/flask/gloss-crud/app.py`, `src/shared/gloss_actions.py`, `tk/operations.py`.
- Language metadata and AI notes: `src/shared/languages.py`, `src/schema/language.schema.json`.

Open questions:
- Do we invoke existing python LLM flows from Electron (subprocess/IPC) or port prompts to JS? Needed for AI buttons and to respect existing guardrails.
 - JS ONLY!!!!!!!!!!!!!!!!!!!!!
- Where should API keys/settings live? Reuse `src/shared/state.json` or new Electron-safe store?
  - electron best practice
- Should we build any read-side index to speed substring searches without loading all glosses, or rely on incremental fs scans per language?
  - 80/20 for now. If you can think of a simple performance boost good, but don't introduce 1000LoC just for this.
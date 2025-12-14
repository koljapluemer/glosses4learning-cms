# Situation Tree Logic

This CMS uses a general, multi-purpose [gloss model](app/renderer/entities/glosses/gloss.schema.json) to manage learning content for a situation-based language learning app.
A *situation* is just a gloss with a `tags` entry "eng:situation"; but when calculating which related data we actually need for a situation context for our learning app, we have some very bespoke logic.
This logic has implications for
- The [visualization of the "situation tree"](app/renderer/features/gloss-tree-panel)
- which glosses are considered to be missing what relations in checks (and subsequent AI-based flows), see e.g. [here](app/renderer/features/ai-batch-tools/AiBatchToolPanel.vue)
- What glosses get exported when running the situation batch exporter implemented [here](app/main-process/ipc/situationHandlers.ts)

It is INTEGRAL!!! that logic shared between these is using shared code and NOT replicated!
Users rely on the tree rendering being a 100% correct, unfailing, undiverging representation of what's gets exported!

At core, the logical "tree" of a situation works like this:
- A situation-tagged gloss (parent situation) has `children`
    - if these are tagged either "eng:understand-expression-goal" or "procedural-paraphrase-expression-goal", they are considered valid goals of this situation
    - the goals themselves then have a semi-recursive gloss tree under them; what exactly is there and should be there and is displayed depends on the goal

Generally, to prevent infinite recursion:
- If we're, at any level, hooking a gloss into the tree that's already in the tree, that's ok, but then consequently *don't* resolve its children. It must be a leaf in this incarnation.

## Goal Red/Green/Yellow State

*information here should be aligned with what is described above*.

A goal can have 3 implicit quality states:
- `RED`: stump goals, insufficient data to practice, will not be exported when exporting a situation
- `YELLOW`: ok for practice, will be exported, should be improved if possible

Per default, a goal is considered `RED`.
This state is specifically not to be calculated for a goal as a whole, but for a specific goal-target_lang-native_lang combination

The specific logic for how to define the implicit state is described below
 
## Per-Goal Tree Logic

### understand-expression-goal

- for the root goal (which must be in target lang), show its translations (into the native lang)
    - It should have translations; otherwise warn (& add to missing translation flow)
        - we do not show or care about any relationships of these translations, they are *not* resolved in any way
- for the root goal, we do a *standard parts recursion* (see below)

- we do *not* show or care about the core goal's `usageExamples`

- any kind of violated "should" results in the goal being `RED` instead of `YELLOW`:
    - no root goal translations
    - any resolved recursive `parts` child of the root goal (resolved as described above) lacking `translations`, `usageExamples` or `parts` (OR the needed check in `log` that this child relationship has been checked and set to be invalid)

### procedural-paraphrase-expression-goal


- for the root goal (must be native lang and have tag "eng:paraphrase"), we should have translations into the target language that are *not* tagged "eng:paraphrase" (otherwise `RED`)
    - for each of these *translations*, do the *standard parts recursion*
- the root goal *should be checked for `parts`* (otherwise goal is `RED`), but it's ok if it has none, this will often happen
    - *if* it has parts, we do the *standard parts recursion* 

### Standard Parts Recursion

- root node should have parts (or have been checked for them)
    - each of these parts (at any depth) should:
        - have a translation (...or have been checked for them)
        - have parts (...or checked)
        - have usageExamples (...or checked) *if they are target language expressions* (if they are native, neither check for nor resolve `usageExamples`)
            - each of these usage examples should have translations (...or have been checked for them)
            - we do *not* show or care about the usage example's `parts`

## Remarks

Let me underline again that a gloss who does not show up in the tree due to inclusion/exclusion rules should NEVER be exported or be put in a batch fix list such as "Fix missing translations".
Bugs like that should categorically be prevented by having one source of truth defining how the per-goal trees are built
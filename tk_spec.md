ok. we need a ui to fix up some stuff the AI got wrong.
let's do a `tk` app, in a new folder `tk/`. although it may access `shared/` and `agent/`.

## tk

Get the currently active situation and langs from `src/shared/state.py`

One screen should be a simple menu for which screen to open.
For now, there is just one screen: "Gloss List Flat"

Fetch all glosses belonging to the situation (no matter which level in the tree, but must be in the tree, and list deduplicated please).
This screen should be a tabular view where each row is the following (exactly).

`content`, and then a bunch of buttons which trigger an an action

- `DEL`, deleting the gloss. make sure this goes through the proper storage logic, and across the codebase references to this gloss are also removed
- `DIRT`, which sets a `needsHumanCheck` (more below) flag on the gloss
- `NOLEARN`, which sets an  `excludeFromLearning` flag on the gloss
- `TRANS ($n)` where $n is the number of relevant translations this gloss currently has. Clicking the button triggers something like `agent/tools/maintenance/fix_missing_translations.py`, only ofc just for this gloss and without the check whether the translation is useful or not. Refactor the existing code smartly (moving stuff into `shared/` if useful) to keep stuff DRY
- `EX ($n)`, the same for usage examples
- `PRT ($n)`, the same for part splitting

## larger changes

- we need to add `needsHumanCheck` and `excludeFromLearning` as optional bools to our general gloss model
- this impacts `src/schema/gloss.schema.json` and the doc `src/schema/gloss_file.md`
- should also be editable via a toggle in [the CRUD cms](src/flask/gloss-crud)
- glosses where either flag is set should appears with a strikethrough effect in the [tree visualization](src/flask/tree)
- glosses where either flag is set should be excluded in [situation export](src/tui/flows/flow_export_situations_batch.py)
A goal can have 3 implicit quality states:
- `RED`: stump goals, insufficient data to practice, will not be exported when exporting a situation
- `YELLOW`: ok for practice, will be exported, should be improved if possible
- `GREEN`: nice!

Per default, a goal is considered `RED`.
This state is specifically not to be calculated for a goal as a whole, but for a specific goal-target_lang-native_lang combination

## understand-expression-goal

### Yellow

If all true:

- the goal expression is in the target lang
- the goal expression itself is translated into the native lang at least once
- the goal expression has >0 `parts`
- each of these `parts` has >0 `translations` back into the native lang

### Green

If all true:

- everything in yellow fulfilled
- the goal expression has at least two translations into the native lang
- each of the `parts` of the goal expression has >=2 `usageExamples` attached which are in turn translated at least once into native language


## procedural-paraphrase-expression-goal

- due to the nature of paraphrases, we have a few special conditions here:
    - we don't want to split the goal expression itself into `parts`, this usually results in meaningless noise (for "express gratitude" we don't need the vocab "express" nor "gratitude")
    - instead, what we want to do is to translate the paraphrase into the target language, but meant as in "how to actually express this" (so not "Dankbarkeit zeigen" but "Danke!", "Vielen Dank!")
    - note: this should be properly reflected in tools such as `agent/tools/queries/list_missing_parts.py`: A procedural paraphrase expression goal needs not to be split! 
    - in the tree, a procedural paraphrase should also
        - *not* display its parts (we don't care)
        - *not* display a warning that is no `parts` (we don't care) 


### Yellow

If:

- the goal expression is in the native lang
- the goal expression itself has a tag `eng:paraphrase`
- the goal expression itself is translated into the target lang at least once
- the goal expression's translation has >0 `parts`
- each of these `parts` has >0 `translations` back into the native lang


### Green

If:

- everything in yellow fulfilled
- the goal expression is translated into the target lang at least twice (and each has `parts` and each of the parts is translated back into native)

## Consequences

- Goals should show up in `src/flask/tree/show_tree.py` with a marker showing their "color state"
- but, importantly [exporting](src/tui/flows/flow_export_situations_batch.py) should *skip* any goals completely which in the situation-lang-lang context are not at least `YELLOW` or `GREEN`
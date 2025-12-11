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

### Yellow

If:

- the goal expression is in the native lang
- the goal expression itself has a tag `eng:paraphrase`
- the goal expression itself is translated into the target lang at least once
- the goal expression has >0 `parts`
- each of these `parts` has >0 `translations` back into the target lang that is *not* tagged `eng:paraphrase`


### Green

If:

- everything in yellow fulfilled
- the goal expression is translated into the target lang at least twice
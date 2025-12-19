Let's fix some logic issues with [batch generation](app/renderer/features/ai-batch-tools/useAiGeneration.ts) and see also [here](app/main-process/storage/glossOperations.ts).

Flows should be as follows:

## Splitting

1. judge whether splitting into parts is appropriate. For those gloss where it's not, add `SPLIT_CONSIDERED_UNNECESSARY` and exclude from further run.
2. pass to the splitting LLM. If a the return value for a given glosses parts is an empty list, also add `SPLIT_CONSIDERED_UNNECESSARY`
3. If user rejects all parts returned for a gloss, also set `SPLIT_CONSIDERED_UNNECESSARY`

## Translation

Similar concept:

1. if LLM returns no translation for a gloss, set `TRANSLATION_CONSIDERED_IMPOSSIBLE`
2. if user rejects all translations, set `TRANSLATION_CONSIDERED_IMPOSSIBLE`


## Usage Examples

Very similar to first:

1. if judged no usage examples can be generated, set `USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE`
2. if no usage examples are returned, set `USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE`
3. if user rejects all, set `USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE`


This is partly implemented, but not completely correctly. Check and improve.
Every Gloss gets a file.
A "gloss" is a unit of meaning in a specific language.

## Schema Properties

A gloss file has a bunch of properties.
In the following, it is described what they're for.
The chapters are only there to group them logically, these "chapters" are not reflected in the actual

### Content

The `content` is the only property that is required.
It's...well, the gloss itself, for example "banana" or "ich renne" or "It rained yesterday" or "-ish"

### General Properties

#### `transcriptions`

- A dictionary structure
- key should be a string describing the kind of transcription, e.g. "IPA narrow"
- value should be the transcription, e.g. "[aɪ̯ pʰiː eɪ̯]"

#### `logs`

- A dictionary where keys are ISO timestamps (`2024-08-01T12:00:00Z`) and values are free-form strings
- Used for lightweight audit or workflow markers such as `SPLIT_CONSIDERED_UNNECESSARY`

#### `needsHumanCheck`

- Boolean flag (optional, defaults to `false`)
- Indicates this gloss needs manual human review, typically flagged by AI tools or automated processes
- Glosses with this flag set are displayed with strikethrough in the tree visualization and excluded from exports

#### `excludeFromLearning`

- Boolean flag (optional, defaults to `false`)
- Marks this gloss to be excluded from learning exports (e.g., situation exports for learning apps)
- Glosses with this flag set are displayed with strikethrough in the tree visualization

### Relationships to other Glosses

Relationships to other glosses are generally encoded as "$iso_code:$slug" (`slug` is equivalent to `content` with characters that are illegal in filenames removed)

### Within-Language

- `morphologically_related`: E.g. connecting "run" to "running" and "runny". This is a symmetrical relationship, A being related to B means B is also related to A.
- `parts`: e.g. for splitting a sentence into its words/sub-expressions
- `has_similar_meaning`: Other glosses meaning the same or almost the same
- `sounds_similar`: Homophones and near homophones. Useful for listening practice.
- `usage_examples`: Other glosses (mostly sentences) showcasing how to use this word
- `to_be_differentiated_from`: Glosses that one should not confuse with this one not necessarily covered by `sounds_similar`. This is a symmetrical relationship.
- `collocations`: Often co-occurs with these glosses. *Not* symmetrical!
- `typical_follow_up`: Can be used to model simple relationships like "How are you?" > "Good, thanks. You?"
- `children`: Used to model relationships that are not necessarily linguistically derived, but didactically useful. E.g. "counting to three" may have *the children* "one", "two", "three". These may cross language boundaries.

### Cross-Language

- `translations`: Expressing this gloss in another language. Symmetrical relationship.
- `notes`: Any kind of free-form annotation such as "only used to address elders in formal contexts". To allow translating these annotations themselves, the notes themselves are modelled as glosses.
- `tags`: Extremely similar to notes themselves, but should be shorter and avoid punctuation and spaces (if that is meaningful in the given language). Allows encoding stuff like "verb", "simple-past", "impolite", "sentence", "common-100-words" or "hard-to-pronounce-for-anglophones". An effort to standardize these tags should be made (for easy parsing).

## General

- More properties may be introduced, these will generally be optional to easily ensure backwards compatibility
- Ensure correct shape with `schema/gloss.schema.json`

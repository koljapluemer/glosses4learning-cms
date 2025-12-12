Let's take our situation management and build an agent based on it.
Make each tool so that an openai sdk agent can use it; [doc](https://openai.github.io/openai-agents-python/tools/)

## General Agent Flow and Goal

1. Let the user create a new situation, and set native and target lang
    - this should work somewhat similar to [this flow](src/tui/flows/flow_set_situation.py), only that the situation is new
2. Let the agent use tools to fill the situation with rich learning content until the situation is "well covered" 

## Rules

- All agent stuff should live in `agent/`
- It's ok also to access functionality from `shared/`
- If you need functionality from *other* folders (which *will* happen), extract the functionality into `shared/` and refactor the original code
    - do not bloat the existing files such as `src/shared/storage.py` and `src/shared/tree.py`, create new shared util files instead
- each tool should have its own file
- prompt and used model and other stuff I as a dev may want to quickly edit should go AT THE TOP of the file as a python constant for easy access
- use state of the art logging so that we can see and audit (persistent logs!!) what the agent is and was doing
- All tools should be testable (unit tests), with mock data and for the LLM calls with mock calls!

## Tools

### Non-LLM Calls

#### Add Gloss To Storage 

- add a [gloss](src/schema/gloss.schema.json) to `src/shared/storage.py`.
- think about whether to add tools for editing glosses as well, or to add stuff to specific relationship lists. 

#### Add Gloss To Storage As Proceduaral Paraphrase Expression Goal

Adds the gloss, sets the tag.

#### Add Gloss To Storage As Understanding Goal

Adds the gloss, sets the tag.

#### Add Usage Examples to Gloss

Adds glosses to db, and hooks them up to `usageExamples` of the gloss that they're examples of.
This gloss should turn up in the `parts` array of the usage examples

#### Get Situation State

See `src/shared/tree.py`/`doc/reference_what_is_a_valid_goal.md` for how this should work.
Gives feedback to the agent of how well-formed the existing learning content is

#### Add Translation to Gloss

For actually adding translations to glosses.

#### Get List of Procedural Paraphrase Expression Goals In Situation

Simple flat list of the existing expression goals in situation, for the agent's overview.

#### Get List of Understanding Goals In Situation

also for overview

#### Get List of Native Paraphrased Glosses With Missing Translations

Replicates tree logic, as below

#### Get List of Native Non-Paraphrased Glosses With Missing Translations
#### Get List of Target Glosses With Missing Translations
#### Get List of Glosses in Situation not yet checked for splitting into parts
#### Get List of Glosses in Situation not yet checked for usage Examples

#### Find Translation Siblings with no notes

- check all native glosses
- if they have multiple translations into the target lang, check if they don't have notes attached
- return a list of lists with "translation siblings" that need usage notes to explain why they're used

#### Add Note Gloss to Gloss

Add the note as gloss if needed, then attach in `notes` of the other note.

#### Add Parts to Gloss

#### Set Gloss as Unsplittable

Does the `SPLIT_CONSIDERED_UNNECESSARY` logic you find in `src/shared/tree.py`

#### Set Gloss as Untranslatable

#### Set Gloss to USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE

### LLM Calls

#### Generate Procedural Paraphrase Expression Goals

Similar to [this](src/tui/flows/flow_add_goals_expression_ai.py): 
- Agent provides language and optional extra context
- gets back a list of glosses (the agent may accept/decline each)

#### Generate Understanding Goals

Like above, with [this](src/tui/flows/flow_add_goals_understand_expression_ai.py)

#### Does It Make Sense to look For Usage Examples?

Gets a list of glosses, and returns a dict like 
{"eng:tree": true}, "eng:The tree is green": true} judging whether a given gloss is a word or phrase that can usefully be used as a building block in an example sentence (as opposed to a whole standalone sentence).

#### Generate Usage Examples For Gloss

Pass in a gloss (a word, not sentences) to get examples of sentences using this gloss

### Are Glosses Splittable?

Gets a list of glosses, and returns a dict like 
{"eng:tree": false}, "eng:I run away": true} judging whether a given gloss can be split into further WORDS or sub-expressions.

#### Split Gloss Into Parts

Analogous to second part of [this](src/tui/flows/flow_split_glosses_of_situation_into_parts_ai.py)

#### Generate Translations For Target Lang Glosses

- should work like the second part of [this](src/tui/flows/flow_translate_untranslated_native_ai.py)
- keep the structure with notes etc that you can already find

#### Generate Translations For Paraphrased Native Glosses

- agent should pass in a list of *paraphrases* expressions here, and then it should work [like this](src/tui/flows/flow_translate_paraphrases_to_target_ai.py)
- see non-llm tool above to get relevant phrases

#### Generate Translations For (Non-Paraphrased) Native Glosses

- like above/like [this](src/tui/flows/flow_translate_untranslated_native_ai.py)

#### Add Usage Notes For Target Glosses

- gets a list of glosses in the target language, returns a dictionary where for each gloss there is a note gloss *in the native language* describing how this gloss is used or what's special about it, e.g.
{
    "deu:Tschüss": "used in casual situations"
    "deu:Auf Wiedersehen!": "semi-formal"
}


#### Judge whether expression goals cover the situation well

Pass situation and list of `content` of expression goal glosses. 
If list excessively long, shuffle and crop.
Answers with first a judgement sentence of whether it considers the code to be complete, then a 1-10 rating

#### Judge whether understanding goals cover the situation well

Same as above, only judges whether the understanding goals do a good job of covering any kind of utterance the learner may hear in this situation



#### Brainstorm ideas

Gets the situation, and optional context, and returns free text with some ideas what kind of dialogs, conversations, utterances and expression desires the learner may encounter in that situation.

## Notes

- when adding anything to db, always consider that this gloss (as identified by the identifier in the style of "deu:Baum" "eng:to run") may already exist
    - if so, don't fail; don't add the gloss as a new one, simply work with the existing one, updating relationship arrays as needed
    - (this should be handled by `shared/` tools)
- Since this is an agentic workflow, tools always should return LLM-readable feedback on what was done or what was skipped or failed
- when running the agent, also [set the state](src/shared/state.py) to the new situation + lang settings, so the tree can be watched via [the flask app](src/flask/tree/show_tree.py)
- keep [readme](README.md) up to date
- don't forget to send the relevant [language AI notes](src/schema/language.schema.json) to LLMs
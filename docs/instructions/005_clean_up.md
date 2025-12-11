Let's clean up this abomination of a project folder.
Goal architecture is the following, in `src/`

```sh
├── flask # very, very minimal setup for a flask app doing a single view-only task: render the tree
│   ├── show_tree.html
│   └── show_tree.py
├── schema
│   ├── gloss.schema.json
│   └── language.schema.json
├── shared
│   ├── log_files/
│   ├── log.py # use BEST PRACTICES to log interesting stuff in here
│   ├── state.py # manage tracking the selected situation and langs in local gitignored file
│   ├── storage.py # reading and writing to data/ and situations/
│   └── tree.py # the bespoke recursion logic of the tree
└── tui
    ├── flows # every flow triggerable from main should get EXACTLY one WELL NAMED file in here
    │   ├── flow_add_goals_expression_ai.py # immediately trigger AI looking for paraphrases (understand what this is!) in the selected native lang a learner may want to express in this situation. After that, standard screen with accept/reject
    │   ├── flow_add_goals_expression_manual.py # single UI with a textarea where the user can add such glosses, one per line (language is automatically native)
    │   ├── flow_add_goals_procedural_paraphrase_ai.py  # same as above, only for non-paraphrases expressions in the selected target lang the learner may need to *understand* in the situation
    │   ├── flow_add_goals_procedural_paraphrase_manual.py # single UI with a textarea where the user can add such glosses, one per line (language is automatically target)
    │   ├── flow_add_situations_ai.py # UI to give AI extra context and select how many situations. Then trigger an AI to come up with new situations. Then standard accept/reject UI
    │   ├── flow_add_situations_manual.py # textarea paradigm, one situation per line
    │   ├── flow_add_usage_examples_ai.py # understand the current flow. First, let user select which glosses should be analyzed, using the existing `USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE` paradigm for the others. Let AI run and show standard confirm/reject
    │   ├── flow_set_settings.py # change the settings (currently only openai key)
    │   ├── flow_set_situation.py # change situation, nat lang, target lang
    │   ├── flow_split_glosses_of_situation_into_parts_ai.py # flow that we already have
    │   ├── flow_translate_untranslated_native_ai.py # immediately try to translate all with AI, after that show confirm/reject. Don't forget to pass language aiNote
    │   └── flow_translate_untranslated_target_ai.py # immediately try to translate all with AI, after that show confirm/reject
    └── main.py # simple cli menu to select flows. auto-redirects to `set_settings`/`set_situation` if unset. Allows quitting.
```

## Non-Negotiable Rules

- add ALL MODEL CHOICES and all PROMPTS for ANY KIND OF AI USAGE in well named constants to THE TOP OF THE RELEVANT FILE!!!!!!!!!!!!
- the goal is that `src/` is self-contained and contains all, yes, ALL code that it needs to run. After complecting this, EVERY!!! folder that isn't `src`, `situations` or `data` WILL be deleted and can henceforth not be referenced!!
- listen to the actual requirements and assume that things have a point. Do not rework the actual business logic because of your flawed hallucinations of what this app should actually be about
- understand what a [gloss](docs/reference/gloss_file.md) actually is
- do not invent features not described in the file tree above
- when having UIs where the user confirms/rejects AI gen, per default have stuff pre-selected!

## Clarifications Needed

- Where should shared settings/state/log files live relative to `src/` (e.g., `src/shared/state.json` and `src/shared/log_files/prompt.log`)? Should they be gitignored, and is there a preferred naming convention? 
don't care, gitignore and name reasonably

- For AI flows, what concrete prompts and model names should be used? Are the defaults in current code acceptable, or should we mirror the prompts from existing Flask/Tk code verbatim?


yes, take over the current ones for now

- Should the Flask `show_tree.py` reuse the same `src/shared` storage/tree code, and is it strictly read-only (no accept/reject actions)?

what "accept/reject" actions?!?!?!?!?!?!?!?!?!?!??! Tree, as the name says, is a fucking tree rendering of the situation with certain children. There cannot possibly be anything to logically acccept or reject. Please actually give a shit and do the slightest bit of understanding what the fucking show tree means!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!1

- For translations and goals, should we reuse the existing language `aiNote` behavior when calling OpenAI (as in current translation_tool.py)?

yes

- For manual flows (textarea inputs), should we enforce any per-line validation (slug/length) or accept all and validate at save time?

validate at save
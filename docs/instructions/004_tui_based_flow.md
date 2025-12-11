In `tools_prompt/break_up_glosses_prompt.py` we successfully prototyped a terminal UI in python.
It allows AI-based splitting of a situation's glosses where that's missing.

Let's build a larger flow, aiming for feature parity with the original flask situation management.
We will build a series of self-contained UIs which however have the ability to trigger other flows/UIs after ending, kind of forming a state machine.

For now, let's implement the following:

## Components

On start of the program, check
- if OPENAI_KEY is set (keep this flexible, we may add other required keys later), otherwise open `Settings Flow`. After done redo this checklist, basically, landing in one of the two following scenarios
- if keys are set but no situation, open `Set Situation Flow`
- otherwise open `Main Menu` 

## Settings Flow

For now, just a single input, the openai key. Persist this on disk in a gitignored file

## Set Situation Flow

Selecting which situation we're managing, including the nat and target language. Persist also in local file

## Menu

A menu showing the name of the situation we're editing, the two languages, and then a simple menu to go to all other tools (and the settings). This is the core thing that things return to

## Tree View

The good old tree view, implemented in `prompt_toolkit`. 
Read only, so all you can do is say "Ok" and go back to menu 

## Automatically Break Up Glosses Into Parts

Basically what's already in `tools_prompt/break_up_glosses_prompt.py`, however ofc w/o the settings (now not needed), 
and also make the AI stuff multi-step:

- at first run a small model returning a structured output `boolean` that only judges whether or not a given gloss *can* reasonably split into further parts for learning. If not, tag it `SPLIT_CONSIDERED_UNNECESSARY` (you will find the logic for that in other parts of the codebase)
- run the splitting logic
- as a small change to the user-confirm-reject UI, always by default have all elements selected instead of unselected

## General Guidelines

- do not implement features not asked for
- do not add UI elements not asked for
- let's remove choosing-a-model from the UI flow. Instead, make that quickly editable via a python constant at the top of relevant flow files. YES, AS A CONSTANT ON TOP OF THE PY FILE, and not also here and there and in an env and in an optional UI, JUST FUCKING THERE
- split up things into extendable, usable files

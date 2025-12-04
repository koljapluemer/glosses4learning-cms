




Let's rebuild the `sbll_cms/templates/specialist/situation_manage.html` tool.
It's already quite nice, but we need the following changes:

## Lang Select

- First of all, if not native + target lang in the selector is set, show nothing but the selector form

## Tree

(the tree view is already fulfilling a lot of these, take care to note the differences)

- On highest level, we want to show glosses that are fulfill any of these
    - they the selected native language and tagged `eng:procedural-paraphrase-expression-goal`. In the display, prepend them with "⚙︎"
    - they are in the selected target lang and tagged `eng:understand-expression-goal`. Prepend them with "🗣" in the view
- Then, do the following bespoke, sometimes-recursive-sometimes-not resolve:
    - for any gloss, native or target, recursively resolve `parts` (and attach as children and grandchildren and so on). write these in bold.
    - for each of the glosses now in the list, show translations to the other language once more (so if a given gloss is in nat language, show its `translations` into target lang, and vice versa). Not in bold, not recursive.
    - for each target lang gloss now existing resolve the `usageExamples` and append them as children, prepending with "🛠" 
    - for each of the stuff added as usage example, recursively resolve `parts` and attach.
    - For each of the glosses added as parts of usage examples, resolve `translations` into the native lang once and attach.

Remove everything else from the page, it's now obsolete. Yes, REMOVE not "comment out" or "migrate".

### Tool Links

Let's start linking to tools from below the tree view.
Our first tool is going to be "Break up glosses with no parts ($number_of_affected_glosses)".

To implement this correctly, we need to amend [the gloss schema](schema/gloss.schema.json) and [its doc](docs/reference/gloss_file.md).
Add an optional prop `logs` which should be an object with ISO timestamps as keys and arbitrary strings as the prop.

Glosses that are not yet "broken up" means all glosses where both is true:

- they do not have `parts`, or it's an empty `[]`
- they do not have "SPLIT_CONSIDERED_UNNECESSARY" in any of their log values


"Break up glosses with no parts  ($number_of_affected_glosses)" is supposed to be a simple button, `POST`ing to a new tool view (new route etc, let's make it clean) a list of such affected glosses from the situation tree.

For now, let's make the view simple: a daisy table, one gloss in a row. One column the `content` which is also a clickable _blank link, another column an sm button "Can't be broken up" which adds such a "SPLIT_CONSIDERED_UNNECESSARY" log to the gloss object. Nothing else yet.
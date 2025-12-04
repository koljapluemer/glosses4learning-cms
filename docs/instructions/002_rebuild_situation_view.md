




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





Let's rebuild the `sbll_cms/templates/specialist/situation_manage.html` tool.
It's already quite nice, but we need the following changes:

## Lang Select

- First of all, if not native + target lang in the selector is set, show nothing but the selector form

## Tree

(the tree view is already fulfilling a lot of these, take care to note the differences)

- On highest level, we want to show glosses that are fulfill any of these
    - they the selected native language and tagged `eng:procedural-paraphrase-expression-goal`. In the display, prepend them with "⚙︎"
    - they are in the selected target lang and tagged `eng:understand-expression-goal`. Prepend them with "🗣" in the view
- Maintain the following lists:
    - `situationGlosses[]`: a reference to all glosses that are in the tree for any reason
    - `glossesToLearn[]`: a list of glosses the learner will specifically have to learn and memorize; relevant later in the frontend. Only specific glosses by specific rules are added here. Displayed bold in the tree
    - `nativeTranslationMissing[]`: target lang glosses that still require a translation into selected native lang. Have a little "⚠" AFTER their content in the tree.
    - `targetTranslationMissing[]`: native lang glosses that still require a translation into selected target lang. Have a little "⚠" AFTER their content in the tree.
    - `partsMissing[]`: any glosses of any of the two langs that may need to be split
    - `usageExampleMissing[]`: target lang glosses that require usage examples. Have a little "🛠?" after their content in the tree.
- Then, do the following bespoke resolve:
    - from the top level goals, recursively resolve their `parts` (and attach as children and grandchildren and so on). 
        - These are `glossesToLearn` throughout.
    - generally recursively process `translations` in a mirrored way (for target lang gloss, attach `translations` that are into the native lang, and vice versa). 
        - To prevent infinite recursion, check if a given gloss is already somewhere in the tree. If so, STILL ATTACH it, but then don't recurse into ITS translations any further.
    - for any *target* lang gloss, also resursively resolve their `usageExamples`, pre-pending them with "🛠" (if they have none, into the `usageExampleMissing` list they go). However ONLY add `usageExamples` to a given gloss if this gloss has no (recursive) parent that is marked as `usageExample` with "🛠". As such, if one traces a leaf up the tree, there should only ever be zero or one glosses marked "🛠". Once "🛠" is in the "lineage", glosses neither display their `usageExamples` in the tree nor are there liable to be in the `usageExampleMissing` list. Apart from that, `usageExamples` should be recursively resolved along their `translations` and `parts` in the same way as everything else. 
    - All the glosses in the tree are liable to be in the respective translationMissing list, if no relevant translations or no relevant log. Of course, we care about whether they actually *have* relevant translations, even if those are not shown in the tree due to recursion limit rule described above.
    - All these glosses are liable to `partsMissing` if no log or `parts` elements



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
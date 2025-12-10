Let's do some spring cleaning of the architecture and file structure here in `sbll_cms`.

Let's get some basics cleared up:

- `gloss`: our core entity
- `language`: a secondary, yet quite important entity
- `tools`: a zoo of bespoke methods usually manipulating a part of a gloss (or multiple). may be used from different parts of the code base.
- `specialized list`: a tabular list view of glosses, usually derived by filtering only those with a certain tag such as "eng:situation"
- `specialized view`: a bespoke view of a gloss in a certain context, again applicable based on tags


We have the following target file tree:

```sh
entities/
|- gloss/ # abstract stuff relating to gloss representation
|   |- # e.g. what's currently in `sbll_cms/constants.py`, could use a better name
|- language/ # abstract stuff relating to lang management
views/ # 1 view file = 1 route. Strictly adhere to this. Keep flat (no subfolders!!) but name in a way that it's well sorted
|- gloss_new.py
|- gloss_edit.py
|- gloss_manage_as_situation.py # this is how specialist views (not the list, the actual management stuff) should be named and sorted!
|- # ..etc.
|- tool_translation.py
|- tool_add_missing_usage_examples.py # tools are NEVER!!!!!! strictly related to a specialist view or another view and current groupings such as `sbll_cms/templates/specialist/missing_target_translations.html` are idiotic!
|- list_situations.py
utils/ # 1 util function = 1 util file. Again, keep flat, but name in a well-sorted name. Only!!!!! to be used for python code that is actually, right now, used by multiple parts of the codebase!!
templates/
|- routes/ # one entry in views/ should correspond to one folder here
|- gloss_new/form.html # ...or whatever
|- tool_translation/ # tools have a standardized file structure
|   |- link_to.html # a standardized link button to this tool
|   |- input_form.html # here the user can set inputs such as which AI model or extra notes. Tools should now always live on their own routes, NOT inline. make this a stub when not reasonably implementable.
|   |- output_form.html # either just a confirmation of whatever was done, or the typical checklists of what to accept.  make this a stub when not reasonably implementable.
|   |- manual.html # letting the user do the tool manually (e.g. manually add translations).  make this a stub when not reasonably implementable.
|- tool_add_missing_usage_examples/ # same file-sub-structure 
|- partials/ # only stuff that is not tools, and actually, right now, reused across the codebase
```

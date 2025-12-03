Let's start establishing "Specialist Views" for special use cases in this CMS.
Have "Specialist Views" be an overview of links, accessible via the nav header.

Our first specialist view (specialist views, may have several sub-routes/sub-views, make sure to cleanly build templates and python files with folders) is going to be called "Situation Management" (remember that this is an internal app for experts, you don't need to yap and waffle and overdescribe what everything is, user's know what they're doing).

going to "situation management" first opens a list of glosses, following the standard daisy-table style for displaying glosses; only it's filtered to only show glosses with the tag "situation".

Each such gloss can be clicked, leading not to the standard gloss edit, but to a bespoke "Manage Situation X" view.

Here, display a custom tree view, using the unicode symbols that the excellent CLI tool `tree` uses (| and elbow connectors and what not).

On first level, show glosses that are in the `children` array of the selected situation and also have "eng:goal" in their `tags` array.
Btw, make all the glosses in this tree view clickable links with target blank to the gloss edit page.

As children of these "goal" glosses show all of their `children`, as long as they have "eng:expression-goal" in their `tags`.
Continue the tree structure by recursively resolving glosses in the `parts` array of these glosses (so also the parts of the parts).
## Architecture

Do NOT!! adhere to the classic folder-by-type architecture Vue comes with.
Instead, use the following folder structure (inspired by Feature-Sliced Design)

- `app`: Stuff that MUST be global, e.g. the vue boilerplate holding the router view. Can import from anywhere, if it must. Should contain little logic.
- `dumb`: collection of simple, reusable stuff. no business logic. may not import from ANY other high-level folder. may cross-import within the folder. put assets here (if needed)
- `entities`: models/entities. Should contain (global) store.
- `features`: ways of interacting with entities. one folder per feature. may NOT import one another. may ONLY import from `dumb` or `entities`.
- `meta`: for complex features interacting in turn with multiple `features`. One folder per meta-feature. May only import from below, and not from other meta-features. Name features CLEARLY and DESCRIPTIVELY (instead of short and confusing) with full noun and full verb action.
- `pages`: One folder per page (a page is something used by the `router.ts` file). If functionality is ONLY used on a given page, put it in the page folder, do not create features or meta-features that are only used by one single page.

Do not use `index.ts` file reexporting components, simply export directly.
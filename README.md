Gloss CMS
=========

Minimal Flask-based CMS for managing glosses stored as JSON files on disk. There is no database; folders inside `data/` are the single source of truth.

Getting started
---------------

```bash
uv sync
uv run flask --app sbll_cms run --debug
```

Then open http://127.0.0.1:5000.

Tk tooling (standalone)
-----------------------

Small Tk helper scripts live in `tools_tk/` and work directly on the same `data/` files:

- `uv run python tools_tk/scripts/view_situation_tree.py` — pick a situation/native/target and view the goal tree + missing counts. Remembers your last selection in `tools_tk/shared/state.json` (gitignored).
- `uv run python tools_tk/scripts/add_understand_expression_goals_for_situation.py` — generate and attach understand-expression goals (target language) to the selected situation; uses OpenAI if configured or simulated data otherwise.

Notes
-----

- Gloss files live in `data/gloss/<iso>/<slug>.json`, where `slug` is the content with illegal filename characters removed.
- A JSON Schema for gloss files is available at `schema/gloss.schema.json`.
- Language definitions live in `data/language/<iso>.json`; see `schema/language.schema.json` for the schema and example files for English and German.
- API keys for OpenAI and DeepL are stored in your browser's localStorage and editable via the Settings link in the header.

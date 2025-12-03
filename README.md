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

Notes
-----

- Gloss files live in `data/<iso>/<slug>.json`, where `slug` is the content with illegal filename characters removed.
- A JSON Schema for gloss files is available at `schema/gloss.schema.json`.

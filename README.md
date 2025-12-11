# Glosses4Learning CMS

CLI/TUI tools (prompt_toolkit) and a tiny Flask view for managing gloss JSON files on disk. Data lives in `data/` (glosses, languages) and `situations/` (situation bundles) pulled via submodules.

## Requirements
- Python (project uses `uv` to run)  
- OpenAI API key (set inside the TUI Settings menu)  

## Quick start (TUI)
1. Run: `uv run python src/tui/main.py`
2. First launch will prompt for API key and situation/lang selection.
3. Menu options cover:
   - Add situations (AI/manual)
   - Add expression goals (AI/manual, native)
   - Add understand goals (AI/manual, target)
   - Split glosses into parts (AI)
   - Translate untranslated (native↔target, AI)
   - Add usage examples (AI)
4. State persists in `src/shared/state.json`; logs in `src/shared/log_files/app.log`.

## Flask apps
- Tree viewer (read-only): `uv run flask --app src.flask.tree.show_tree run --debug --port 5010`  
- Gloss CRUD UI: `uv run flask --app src/flask/gloss-crud/app.py run --debug --port 5011`  
- Situation goals overview (read-only): `uv run flask --app src/flask/situation-goals/app.py run --debug --port 5012`

Port collisions: every app defaults to 5000, so always pass `--port` (or `FLASK_RUN_PORT`) and stick to fixed ports per tool (e.g., 5010 tree, 5011 CRUD, 5012 goals). If something else is using a port, just bump the number when launching.

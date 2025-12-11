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

## Tree viewer (Flask)
- Run: `uv run flask --app src.flask.show_tree run --debug`
- Open: http://127.0.0.1:5000  
- Read-only view of the current situation tree.

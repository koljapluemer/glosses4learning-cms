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

## Agent System (NEW)

The agent system provides autonomous analysis and recommendations for filling language learning situations with rich content.

### Quick Start (Agent)

```bash
# Analyze a situation and get recommendations
uv run python -m agent.cli \
  --situation "eng:cooking-together" \
  --native eng \
  --target deu

# With custom API key
uv run python -m agent.cli \
  --situation "eng:at-the-airport" \
  --native eng \
  --target arb \
  --api-key YOUR_OPENAI_KEY
```

### What the Agent Does

The agent analyzes your learning situation and provides:
- **State Assessment**: Red/Yellow/Green validation of all goals
- **Gap Analysis**: Identifies missing translations, parts, usage examples
- **Recommendations**: Specific next steps to improve content
- **Structured Logging**: JSON logs for full auditability

### Agent Architecture

**Available Tools (20 implemented, 9 LLM tools remaining):**

**Database Tools (11):**
- `add_gloss` - Create glosses
- `add_translation` - Add bidirectional translations with notes
- `add_parts` - Split glosses into components
- `add_usage_examples` - Add example sentences
- `add_gloss_as_procedural_goal` - Add expression goals
- `add_gloss_as_understanding_goal` - Add comprehension goals
- `add_note` - Add usage notes
- `mark_unsplittable` - Mark atomic glosses
- `mark_untranslatable` - Mark untranslatable content
- `mark_no_usage_examples` - Mark complete sentences
- `attach_to_situation` - Link glosses to situations

**Query Tools (7):**
- `get_situation_state` - Full state with goal validation (CRITICAL)
- `list_procedural_goals` - List expression goals
- `list_understanding_goals` - List comprehension goals
- `list_missing_translations` - Find glosses needing translation
- `list_missing_parts` - Find glosses needing splitting
- `list_missing_usage` - Find glosses needing examples
- `find_translation_siblings` - Find translations needing notes

**LLM Tools (4 implemented, 9 more planned):**
- `generate_procedural_goals` - Create expression goals
- `generate_understanding_goals` - Create comprehension goals
- `translate_paraphrased_native` - Translate communicative goals
- `translate_native_glosses` - Translate standard glosses

### Logs and Monitoring

Agent sessions create structured JSON logs in `agent/logs/`:
- `agent_YYYYMMDD.log` - Daily rotating log
- `agent_session_TIMESTAMP.log` - Per-session log

Each log entry includes:
- Timestamp (UTC)
- Tool name and operation
- Gloss/situation references
- Success/error details

View logs:
```bash
# Latest session
ls -t agent/logs/agent_session_*.log | head -1 | xargs cat

# Specific date
cat agent/logs/agent_20241212.log
```

### Integration with Flask

After running the agent, view results:
```bash
uv run flask --app src.flask.tree.show_tree run --debug --port 5010
```

The tree viewer shows the current state with visual indicators for red/yellow/green goals.

### Current Status

**MVP Complete:** The agent can analyze situations, generate goals, create translations, and provide detailed recommendations.

**Future Enhancements:**
- Remaining 9 LLM tools (splitting, usage examples, judgments)
- Fully autonomous operation loop
- Unit tests with mocked LLM calls
- Interactive approval workflow

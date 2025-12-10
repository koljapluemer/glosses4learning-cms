## How to add a new tool (internal cheatsheet)

Follow the conventions from `docs/instructions/003_clean_up_architecture.md` so every tool is structured the same way, with the HTMX/JSON flow and zero hidden blobs.

### 1) Pick a clear tool name
- Use a domain name, not a framework name, e.g. `tool_missing_target_translations.py`.
- The view file lives in `sbll_cms/views/` and should contain only this tool.

### 2) Create the three routes
- All tool routes hang off `tools_bp` (see `sbll_cms/views/blueprints.py`).
- Add three view functions in your tool file:
  - `/<tool>/.../input` — GET-only; shows the input form (model/context/etc.). Use GET so params land in the URL, no hidden JSON.
  - `/<tool>/.../output` — GET renders the page; POST (JSON only) runs actions (`generate`, `accept_all`, `accept_selection`, optional `mark_impossible`, `discard`) and returns JSON `{ai_results, ai_message, ai_error}`.
  - `/<tool>/.../manual` — purely manual workflow (no API key needed).
- Keep each route focused; reuse helpers from `sbll_cms/entities/...` when the logic is gloss-specific.

### 3) Provide the standard templates
Create a folder `sbll_cms/templates/<tool_name>/` with these files:
- `link_to_manual.html` and `link_to_auto.html` — simple `<a>` buttons to the manual and input routes.
- `input_form.html` — collects parameters (target language, model, context, etc.). Keep it GET-only.
- `output_form.html` — renders the list of candidate glosses/options and wires up the JS helper.
- `manual.html` — manual workflow mirroring the entity’s usual edit flow.

### 4) Use the shared JS helper
- Load `{{ url_for('static', filename='js/tool_ai_flow.js') }}` in `output_form.html`.
- Call `initAiTool({ postUrl, resultsContainer, messageContainer, generateButton, acceptAllButton, acceptSelectedButton, discardButton, getMetaPayload, getGeneratePayload, resultField, extractValues, titleForResult })`.
- `initAiTool`:
  - POSTs JSON to `postUrl` for `generate`, `accept_all`, `accept_selection`.
  - Renders checkboxes for AI values so the browser carries the user’s selection (no hidden `results_json` fields).
  - Exposes `post`, `showMessage`, `clearResults`, `getResults` on the returned object so you can wire extra buttons (e.g. `mark_impossible`).

### 5) Keep logic in the right layer
- Entity-specific helpers belong under `sbll_cms/entities/...`, not `utils/`.
- `utils/` is only for helpers used by multiple parts of the app.

### 6) Test it
- Run `uv run python -m flask --app sbll_cms run --debug` and click through manual/input/output.
- Verify JSON POSTs succeed (no hidden form blobs) and the page reloads cleanly after accept/mark/discard.

<!-- fill in doc -->
## How to add a new tool (internal cheatsheet)

Follow the conventions from `docs/instructions/003_clean_up_architecture.md` so every tool is structured the same way.

### 1) Pick a clear tool name
- Use a domain name, not a framework name, e.g. `tool_missing_target_translations.py`.
- The view file lives in `sbll_cms/views/` and should contain only this tool.

### 2) Create the three routes
- All tool routes hang off `tools_bp` (see `sbll_cms/views/blueprints.py`).
- Add three view functions in your tool file:
  - `/<tool>/<language>/<slug>/input` — shows the input form (model/context/etc.).
  - `/<tool>/<language>/<slug>/output` — shows results and lets the user accept/discard.
  - `/<tool>/<language>/<slug>/manual` — purely manual workflow (no API key needed).
- Keep each route focused; reuse helpers from `sbll_cms/entities/...` when the logic is gloss-specific.

### 3) Provide the standard templates
Create a folder `sbll_cms/templates/<tool_name>/` with these files:
- `link_to_manual.html` and `link_to_auto.html` — simple `<a>` buttons to the manual and input routes.
- `input_form.html` — collects parameters (target language, model, context, etc.). Stub is okay if not yet auto-capable.
- `output_form.html` — displays generated output and lets the user accept/reject. Stub is okay if nothing to review.
- `manual.html` — manual workflow mirroring the entity’s usual edit flow.

### 4) Register the tool
- Ensure the tool module is imported in `sbll_cms/views/__init__.py` so Flask registers its routes.
- Link to the tool where appropriate (e.g. from gloss detail pages) using the `link_to_*` templates.

### 5) Keep logic in the right layer
- Entity-specific helpers belong under `sbll_cms/entities/...`, not `utils/`.
- `utils/` is only for helpers used by multiple parts of the app.

### 6) Test it
- Run `uv run python -m flask --app sbll_cms run --debug` and click through manual/input/output.
- Add minimal flash/error handling for missing gloss, languages, or API keys.

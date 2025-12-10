from __future__ import annotations

import json

import requests
from flask import current_app, flash, redirect, render_template, request, url_for

from sbll_cms.entities.gloss import Gloss, attach_relation
from sbll_cms.entities.language import get_language_store
from sbll_cms.storage import get_storage
from sbll_cms.views.blueprints import tools_bp


def _generate_procedural_goals_openai(
    api_key: str,
    model: str,
    situation_content: str,
    native_language: str,
    target_language: str,
    num_goals: int,
    context: str,
    ai_note: str = ""
) -> dict:
    """Generate procedural-paraphrase-expression-goals in native language."""
    prompt = f"""Generate {num_goals} procedural-paraphrase-expression-goals in {native_language} for the situation: "{situation_content}".

These are procedural descriptions in the learner's native language ({native_language}) of things they might want to do in {target_language}.
Each goal should be a brief procedural phrase like "ask what the thing you're pointing at is" or "offer someone a drink".

Think about common communicative actions a learner might need in this situation.

{ai_note}

Additional context: {context}

Return a JSON object with a 'goals' array containing the {native_language} procedural descriptions."""

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model or "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a language learning curriculum designer who creates procedural paraphrase goals for language learners."
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 500,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "goal_list",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "goals": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            },
                            "required": ["goals"],
                            "additionalProperties": False,
                        },
                        "strict": True,
                    },
                },
            },
            timeout=30,
        )

        data = response.json()
        if response.status_code != 200:
            return {
                "goals": [],
                "error": data.get("error", {}).get("message", "OpenAI API error")
            }

        content = data["choices"][0]["message"]["content"].strip()
        parsed = json.loads(content)
        goals_list = parsed.get("goals", [])

        formatted = [{"content": g.strip()} for g in goals_list if g.strip()]

        return {
            "goals": formatted,
            "error": None
        }

    except Exception as exc:  # noqa: BLE001
        return {
            "goals": [],
            "error": str(exc)
        }


@tools_bp.route("/add-procedural-goals/<language>/<slug>/input", methods=["GET"])
def add_procedural_goals_input(language: str, slug: str):
    """Route 1: Collect AI generation parameters."""
    storage = get_storage()
    situation = storage.load_gloss(language, slug)
    if not situation:
        flash("Situation not found.", "error")
        return redirect(url_for("situations.list_situations")), 404

    target_language = request.args.get("target_language", "").strip()
    native_language = request.args.get("native_language", "").strip()

    return render_template(
        "tool_add_procedural_goals/input_form.html",
        situation=situation,
        target_language=target_language,
        native_language=native_language,
        provider_model="OpenAI|gpt-4o-mini",
        context="",
        num_goals=5,
    )


@tools_bp.route("/add-procedural-goals/<language>/<slug>/output", methods=["GET", "POST"])
def add_procedural_goals_output(language: str, slug: str):
    """Route 2: Generate goals via AI, review, accept/discard."""
    storage = get_storage()
    situation = storage.load_gloss(language, slug)
    if not situation:
        flash("Situation not found.", "error")
        return redirect(url_for("situations.list_situations")), 404

    settings = current_app.extensions["settings_store"].load()

    json_mode = request.method == "POST" and request.is_json

    if json_mode:
        payload = request.get_json(force=True) or {}
        provider_model = payload.get("provider_model", "OpenAI|gpt-4o-mini")
        target_language = (payload.get("target_language") or "").strip()
        native_language = (payload.get("native_language") or "").strip()
        context = payload.get("context", "")
        num_goals = int(payload.get("num_goals", 5))
        action = (payload.get("mode") or payload.get("action") or "").strip()
        results_json = json.dumps(payload.get("results") or [])
        selected_contents = []
        for entry in payload.get("selections", []):
            if isinstance(entry, str):
                selected_contents.append(entry)
            elif isinstance(entry, dict):
                val = (entry.get("value") or "").strip()
                if val:
                    selected_contents.append(val)
    else:
        provider_model = request.values.get("provider_model", "OpenAI|gpt-4o-mini")
        target_language = (request.values.get("target_language") or "").strip()
        native_language = (request.values.get("native_language") or "").strip()
        context = request.values.get("context", "")
        num_goals = int(request.values.get("num_goals", 5))
        action = ""
        results_json = request.values.get("results_json", "[]")
        selected_contents = []

    if "|" in provider_model:
        provider, model = provider_model.split("|", 1)
    else:
        provider, model = provider_model, ""

    try:
        ai_results = json.loads(results_json) if results_json else []
    except Exception:  # noqa: BLE001
        ai_results = []

    ai_error = None
    ai_message = None

    try:
        if json_mode:
            if action in ("ai_generate", "generate"):
                # Validate
                if not settings or not settings.api_keys.openai:
                    ai_error = "OpenAI API key missing. Add it in Settings."
                elif provider != "OpenAI":
                    ai_error = "Only OpenAI is supported for now."
                elif not native_language:
                    ai_error = "Native language is required."
                else:
                    # Get language AI note if available
                    ai_note = ""
                    lang_store = get_language_store()
                    native_lang_obj = lang_store.get(native_language)
                    if native_lang_obj and hasattr(native_lang_obj, "ai_note"):
                        ai_note = native_lang_obj.ai_note or ""

                    # Generate goals
                    result = _generate_procedural_goals_openai(
                        api_key=settings.api_keys.openai,
                        model=model,
                        situation_content=situation.content,
                        native_language=native_language,
                        target_language=target_language,
                        num_goals=num_goals,
                        context=context,
                        ai_note=ai_note
                    )

                    if result.get("error"):
                        ai_error = result["error"]
                        ai_results = []
                    else:
                        ai_results = result.get("goals", [])

            elif action in ("ai_accept_all", "ai_accept_selection", "accept_all", "accept_selection"):
                if action in ("ai_accept_all", "accept_all"):
                    to_create = [r["content"] for r in ai_results]
                else:
                    to_create = selected_contents

                created_count = 0
                skipped_count = 0

                for goal_text in to_create:
                    goal_text = goal_text.strip()
                    if not goal_text:
                        continue

                    # Check if goal already exists
                    existing = storage.find_gloss_by_content(native_language, goal_text)
                    if existing:
                        # Ensure BOTH tags are present
                        tags = existing.tags or []
                        needs_update = False

                        if "eng:paraphrase" not in tags:
                            tags.append("eng:paraphrase")
                            needs_update = True
                        if "eng:procedural-paraphrase-expression-goal" not in tags:
                            tags.append("eng:procedural-paraphrase-expression-goal")
                            needs_update = True

                        if needs_update:
                            existing.tags = tags
                            storage.save_gloss(existing)
                            created_count += 1
                        else:
                            skipped_count += 1
                        goal = existing
                    else:
                        # Create new goal gloss with BOTH tags
                        goal = storage.create_gloss(Gloss(
                            content=goal_text,
                            language=native_language,
                            tags=["eng:paraphrase", "eng:procedural-paraphrase-expression-goal"]
                        ))
                        created_count += 1

                    # Link to situation via children field
                        attach_relation(storage, situation, "children", goal)

                ai_message = f"Created {created_count} goals. Skipped {skipped_count} existing. Linked to situation."
                ai_results = []  # Clear after accepting

            elif action in ("ai_discard", "discard"):
                ai_results = []
    except Exception as exc:  # noqa: BLE001
        ai_error = str(exc)
        ai_results = []

    if json_mode:
        status = 200 if not ai_error else 400
        return {
            "ai_results": ai_results,
            "ai_error": ai_error,
            "ai_message": ai_message,
        }, status

    return render_template(
        "tool_add_procedural_goals/output_form.html",
        situation=situation,
        target_language=target_language,
        native_language=native_language,
        provider_model=provider_model,
        context=context,
        num_goals=num_goals,
    )


@tools_bp.route("/add-procedural-goals/<language>/<slug>/manual", methods=["GET", "POST"])
def add_procedural_goals_manual(language: str, slug: str):
    """Route 3: Batch manual creation of procedural-paraphrase-expression-goals."""
    storage = get_storage()
    situation = storage.load_gloss(language, slug)
    if not situation:
        flash("Situation not found.", "error")
        return redirect(url_for("situations.list_situations")), 404

    target_language = request.form.get("target_language") or request.args.get("target_language", "").strip()
    native_language = request.form.get("native_language") or request.args.get("native_language", "").strip()

    message = None
    error = None

    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "create":
            # Get all goal contents from form
            goal_contents = request.form.getlist("goal_content")

            if not goal_contents or not any(g.strip() for g in goal_contents):
                error = "At least one goal is required."
            elif not native_language:
                error = "Native language is required."
            else:
                created_count = 0
                skipped_count = 0

                for goal_text in goal_contents:
                    goal_text = goal_text.strip()
                    if not goal_text:
                        continue

                    # Check if already exists
                    existing = storage.find_gloss_by_content(native_language, goal_text)
                    if existing:
                        # Ensure BOTH tags are present
                        tags = existing.tags or []
                        needs_update = False

                        if "eng:paraphrase" not in tags:
                            tags.append("eng:paraphrase")
                            needs_update = True
                        if "eng:procedural-paraphrase-expression-goal" not in tags:
                            tags.append("eng:procedural-paraphrase-expression-goal")
                            needs_update = True

                        if needs_update:
                            existing.tags = tags
                            storage.save_gloss(existing)
                            created_count += 1
                        else:
                            skipped_count += 1
                        goal = existing
                    else:
                        # Create new goal with BOTH tags
                        goal = storage.create_gloss(Gloss(
                            content=goal_text,
                            language=native_language,
                            tags=["eng:paraphrase", "eng:procedural-paraphrase-expression-goal"]
                        ))
                        created_count += 1

                    # Link to situation
                    attach_relation(storage, situation, "children", goal)

                message = f"Created {created_count} goals. Skipped {skipped_count} existing. Linked to situation."

    return render_template(
        "tool_add_procedural_goals/manual.html",
        situation=situation,
        target_language=target_language,
        native_language=native_language,
        message=message,
        error=error,
    )

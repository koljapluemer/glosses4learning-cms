from __future__ import annotations

import json

import requests
from flask import current_app, flash, redirect, render_template, request, url_for

from sbll_cms.entities.gloss import Gloss
from sbll_cms.storage import get_storage
from sbll_cms.views.blueprints import tools_bp


def _generate_situations_openai(api_key: str, model: str, context: str, num_situations: int) -> dict:
    """
    Generate situation descriptions using OpenAI API.

    Returns:
        {
            "situations": [{"content": "situation text"}, ...],
            "error": None or error message
        }
    """
    # Build prompt
    if context:
        prompt = (
            f"Generate {num_situations} realistic, practical situation descriptions for language learning. "
            f"Context/theme: {context}. "
            "Each situation should be a short phrase describing a common real-world scenario "
            "(e.g., 'at the airport', 'ordering coffee', 'asking for directions'). "
            "Return a JSON object with a 'situations' array containing the descriptions."
        )
    else:
        prompt = (
            f"Generate {num_situations} realistic, practical situation descriptions for language learning. "
            "Each situation should be a short phrase describing a common real-world scenario "
            "(e.g., 'at the airport', 'ordering coffee', 'asking for directions'). "
            "Focus on everyday, practical situations where language learners need specific vocabulary and phrases. "
            "Return a JSON object with a 'situations' array containing the descriptions."
        )

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
                        "content": "You are a language learning curriculum designer who creates practical situation descriptions."
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 500,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "situation_list",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "situations": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            },
                            "required": ["situations"],
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
                "situations": [],
                "error": data.get("error", {}).get("message", "OpenAI API error")
            }

        content = data["choices"][0]["message"]["content"].strip()
        parsed = json.loads(content)
        situations_list = parsed.get("situations", [])

        # Format for output
        formatted = [{"content": s.strip()} for s in situations_list if s.strip()]

        return {
            "situations": formatted,
            "error": None
        }

    except Exception as exc:  # noqa: BLE001
        return {
            "situations": [],
            "error": str(exc)
        }


@tools_bp.route("/create-situation/input", methods=["GET"])
def create_situation_input():
    """Route 1: Collect AI generation parameters."""
    return render_template(
        "tool_create_situation/input_form.html",
        provider_model="OpenAI|gpt-4o-mini",
        context="",
        num_situations=3,
    )


@tools_bp.route("/create-situation/output", methods=["GET", "POST"])
def create_situation_output():
    """Route 2: Generate situations via AI, review, accept/discard."""
    storage = get_storage()
    settings = current_app.extensions["settings_store"].load()

    # Extract form parameters
    provider_model = request.form.get("provider_model", "OpenAI|gpt-4o-mini")
    if "|" in provider_model:
        provider, model = provider_model.split("|", 1)
    else:
        provider, model = provider_model, ""

    context = request.form.get("context", "")
    num_situations = int(request.form.get("num_situations", 3))
    action = request.form.get("action", "")
    results_json = request.form.get("results_json", "[]")

    # Parse existing AI results
    try:
        ai_results = json.loads(results_json) if results_json else []
    except Exception:  # noqa: BLE001
        ai_results = []

    ai_error = None
    ai_message = None

    try:
        if request.method == "POST":
            if action == "ai_generate":
                # Validate
                if not settings or not settings.api_keys.openai:
                    ai_error = "OpenAI API key missing. Add it in Settings."
                elif provider != "OpenAI":
                    ai_error = "Only OpenAI is supported for now."
                else:
                    # Generate situations
                    result = _generate_situations_openai(
                        api_key=settings.api_keys.openai,
                        model=model,
                        context=context,
                        num_situations=num_situations
                    )

                    if result.get("error"):
                        ai_error = result["error"]
                        ai_results = []
                    else:
                        ai_results = result.get("situations", [])

            elif action in ("ai_accept_all", "ai_accept_selection"):
                # Get selected situations
                selected_contents = request.form.getlist("selected_situation")

                if action == "ai_accept_all":
                    to_create = [r["content"] for r in ai_results]
                else:
                    to_create = selected_contents

                created_count = 0
                skipped_count = 0

                for content in to_create:
                    content = content.strip()
                    if not content:
                        continue

                    # Check if already exists
                    existing = storage.find_gloss_by_content("eng", content)
                    if existing:
                        # Add tag if missing
                        if "eng:situation" not in (existing.tags or []):
                            existing.tags = (existing.tags or []) + ["eng:situation"]
                            storage.save_gloss(existing)
                            created_count += 1
                        else:
                            skipped_count += 1
                        continue

                    # Create new situation gloss
                    new_gloss = Gloss(
                        content=content,
                        language="eng",
                        tags=["eng:situation"]
                    )
                    storage.create_gloss(new_gloss)
                    created_count += 1

                ai_message = f"Created {created_count} new situations. Skipped {skipped_count} existing."
                ai_results = []  # Clear after accepting

            elif action == "ai_discard":
                ai_results = []
    except Exception as exc:  # noqa: BLE001
        ai_error = str(exc)
        ai_results = []

    ai_results_json = json.dumps(ai_results)

    return render_template(
        "tool_create_situation/output_form.html",
        provider_model=provider_model,
        context=context,
        num_situations=num_situations,
        ai_results=ai_results,
        ai_results_json=ai_results_json,
        ai_error=ai_error,
        ai_message=ai_message,
    )


@tools_bp.route("/create-situation/manual", methods=["GET", "POST"])
def create_situation_manual():
    """Route 3: Batch manual creation of situations."""
    storage = get_storage()

    message = None
    error = None

    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "create":
            # Get all situation contents from form
            situation_contents = request.form.getlist("situation_content")

            if not situation_contents or not any(s.strip() for s in situation_contents):
                error = "At least one situation is required."
            else:
                created_count = 0
                skipped_count = 0

                for content in situation_contents:
                    content = content.strip()
                    if not content:
                        continue

                    # Check if already exists
                    existing = storage.find_gloss_by_content("eng", content)
                    if existing:
                        # Add tag if missing
                        if "eng:situation" not in (existing.tags or []):
                            existing.tags = (existing.tags or []) + ["eng:situation"]
                            storage.save_gloss(existing)
                            created_count += 1
                        else:
                            skipped_count += 1
                        continue

                    # Create new situation
                    new_gloss = Gloss(
                        content=content,
                        language="eng",
                        tags=["eng:situation"]
                    )
                    storage.create_gloss(new_gloss)
                    created_count += 1

                message = f"Created {created_count} situations. Skipped {skipped_count} existing."

    return render_template(
        "tool_create_situation/manual.html",
        message=message,
        error=error,
    )

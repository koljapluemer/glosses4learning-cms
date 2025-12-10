from __future__ import annotations

import json
from datetime import datetime

import requests
from flask import current_app, flash, redirect, render_template, request, url_for

from sbll_cms.entities.gloss import Gloss, attach_relation
from sbll_cms.storage import get_storage
from sbll_cms.views.blueprints import tools_bp

SPLIT_LOG_MARKER = "SPLIT_CONSIDERED_UNNECESSARY"


def should_break_up(gloss) -> bool:
    no_parts = not (getattr(gloss, "parts", None) or [])
    logs = getattr(gloss, "logs", {}) or {}
    skip_marked = False
    if isinstance(logs, dict):
        skip_marked = any(SPLIT_LOG_MARKER in str(val) for val in logs.values())
    return no_parts and not skip_marked


def generate_split(gloss, model: str, api_key: str, context: str = "") -> dict:
    prompt = (
        f"Take this {gloss.language} expression or phrase and break it up into parts "
        "that can be learned on their own, such as sub-expressions or words. "
        "Return a JSON object with a 'parts' array of strings. Avoid repetition."
    )
    if context:
        prompt += f" Context: {context}"
    prompt += f" Expression: {gloss.content}"
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
                    {"role": "system", "content": "You are a concise linguistic decomposition assistant."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 200,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "parts_list",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "parts": {"type": "array", "items": {"type": "string"}}
                            },
                            "required": ["parts"],
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
            return {"parts": [], "error": data.get("error", {}).get("message", "OpenAI error")}
        content = data["choices"][0]["message"]["content"].strip()
        try:
            parsed = json.loads(content)
            parts = parsed.get("parts", []) if isinstance(parsed, dict) else []
        except Exception:
            parts = []
        parts = [p.strip() for p in parts if isinstance(p, str) and p.strip()]
        return {"parts": parts, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"parts": [], "error": str(exc)}


def _load_refs():
    raw = request.values.get("refs") or "[]"
    try:
        parsed = json.loads(raw)
    except Exception:
        return []
    return [r.strip() for r in parsed if isinstance(r, str) and r.strip()]


@tools_bp.route("/break-up-glosses/manual", methods=["GET", "POST"])
def break_up_glosses_manual():
    storage = get_storage()
    refs = _load_refs()
    glosses = []
    for ref in refs:
        gloss = storage.resolve_reference(ref)
        if gloss and should_break_up(gloss):
            glosses.append(gloss)

    if request.method == "POST":
        action = (request.form.get("action") or "").strip()
        target_ref = (request.form.get("ref") or "").strip()
        if action == "mark_skip":
            targets = [target_ref] if target_ref else []
            for ref in targets:
                gloss = storage.resolve_reference(ref)
                if gloss:
                    logs = gloss.logs if isinstance(getattr(gloss, "logs", {}), dict) else {}
                    logs[datetime.utcnow().isoformat() + "Z"] = SPLIT_LOG_MARKER
                    gloss.logs = logs
                    storage.save_gloss(gloss)
            return redirect(url_for("tools.break_up_glosses_manual", refs=json.dumps(refs)))

    return render_template(
        "tool_break_up_glosses/manual.html",
        glosses=glosses,
        refs_json=json.dumps(refs),
    )


@tools_bp.route("/break-up-glosses/input", methods=["GET"])
def break_up_glosses_input():
    refs = _load_refs()
    return render_template(
        "tool_break_up_glosses/input_form.html",
        refs_json=json.dumps(refs),
        provider_model="OpenAI|gpt-4o-mini",
        context="",
    )


@tools_bp.route("/break-up-glosses/output", methods=["GET", "POST"])
def break_up_glosses_output():
    storage = get_storage()
    refs = _load_refs()
    action = (request.form.get("action") or "").strip()
    provider_model = request.form.get("provider_model") or "OpenAI|gpt-4o-mini"
    provider, model = provider_model.split("|", 1)
    context_text = request.form.get("context") or ""
    results_raw = request.form.get("results_json") or "[]"
    selected_parts = [p for p in (request.form.getlist("selected_part") or []) if p.strip()]
    selected_refs = [r.strip() for r in (request.form.getlist("selected_ref") or []) if r.strip()]

    try:
        ai_results = json.loads(results_raw)
    except Exception:
        ai_results = []

    ai_error = None
    ai_message = None

    settings = current_app.extensions["settings_store"].load()

    glosses = []
    seen = set()
    for ref in refs:
        if ref in seen:
            continue
        seen.add(ref)
        gloss = storage.resolve_reference(ref)
        if gloss and should_break_up(gloss):
            glosses.append(gloss)

    if request.method == "POST":
        if action == "ai_generate":
            if not selected_refs:
                ai_error = "Select glosses to split."
            elif provider != "OpenAI":
                ai_error = "Only OpenAI is supported for now."
            elif not settings.api_keys.openai:
                ai_error = "OpenAI API key missing. Add it in Settings."
            else:
                ai_results = []
                for ref in selected_refs:
                    gloss = storage.resolve_reference(ref)
                    if not gloss or not should_break_up(gloss):
                        continue
                    result = generate_split(gloss, model, settings.api_keys.openai, context_text)
                    ai_results.append({
                        "ref": f"{gloss.language}:{gloss.slug}",
                        "content": gloss.content,
                        "language": gloss.language,
                        "parts": result.get("parts") or [],
                        "error": result.get("error"),
                    })
                if not ai_results:
                    ai_error = "No eligible glosses found to split."
        elif action in ("ai_accept_all", "ai_accept_selection"):
            if not ai_results:
                ai_error = "No AI results to accept."
            else:
                added = 0
                selection_map: dict[str, list[str]] = {}
                if action == "ai_accept_selection":
                    for val in selected_parts:
                        try:
                            entry = json.loads(val)
                        except Exception:
                            continue
                        if not isinstance(entry, dict):
                            continue
                        ref = entry.get("ref")
                        part = entry.get("part")
                        if not ref or not isinstance(part, str):
                            continue
                        selection_map.setdefault(ref, []).append(part)
                for item in ai_results:
                    ref = item.get("ref", "")
                    gloss = storage.resolve_reference(ref)
                    if not gloss:
                        continue
                    parts = item.get("parts") or []
                    chosen = parts if action == "ai_accept_all" else selection_map.get(ref, [])
                    for part_text in chosen:
                        part_text = part_text.strip()
                        if not part_text:
                            continue
                        part_gloss = storage.ensure_gloss(gloss.language, part_text)
                        attach_relation(storage, gloss, "parts", part_gloss)
                        added += 1
                ai_results = []
                ai_message = f"Added {added} parts." if added else "No parts added."
        elif action == "ai_discard":
            ai_results = []

    return render_template(
        "tool_break_up_glosses/output_form.html",
        glosses=glosses,
        refs_json=json.dumps(refs),
        provider_model=provider_model,
        context=context_text,
        ai_results=ai_results,
        ai_results_json=json.dumps(ai_results),
        ai_error=ai_error,
        ai_message=ai_message,
    )

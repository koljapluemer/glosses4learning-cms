from __future__ import annotations

import json
from datetime import datetime

import requests
from flask import current_app, flash, redirect, render_template, request, url_for

from sbll_cms.entities.gloss import Gloss, attach_relation
from sbll_cms.entities.language import get_language_store
from sbll_cms.storage import get_storage
from sbll_cms.views.blueprints import tools_bp

USAGE_IMPOSSIBLE_MARKER = "USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE"


def should_add_usage_examples(gloss, target_language: str) -> bool:
    if gloss.language != target_language:
        return False
    tags = gloss.tags or []
    if "eng:paraphrase" in tags:
        return False
    examples = getattr(gloss, "usage_examples", []) or []
    if examples:
        return False
    logs = getattr(gloss, "logs", {}) or {}
    if isinstance(logs, dict):
        blocked = any(f"{USAGE_IMPOSSIBLE_MARKER}:{target_language}" in str(val) for val in logs.values())
        if blocked:
            return False
    return True


def _parse_refs(raw: str) -> list[str]:
    try:
        parsed = json.loads(raw)
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []
    return [r.strip() for r in parsed if isinstance(r, str) and r.strip()]


def generate_usage_examples(gloss, model: str, api_key: str, context: str, language_store):
    ai_note = ""
    lang_obj = language_store.get(gloss.language)
    if lang_obj and getattr(lang_obj, "ai_note", None):
        ai_note = lang_obj.ai_note

    prompt = (
        f"Return three short, easily understandable, real, natural language examples that utilize the expression '{gloss.content}' "
        "in {language}. Each example should be a single sentence and practical for learners. "
        "Respond as JSON with an 'examples' array of strings."
    ).format(language=gloss.language)
    if ai_note:
        prompt += f" Notes for this language: {ai_note}."
    if context:
        prompt += f" Additional context: {context}"
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
                    {"role": "system", "content": "You are a concise language learning assistant returning structured examples."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 220,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "usage_examples",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "examples": {"type": "array", "items": {"type": "string"}}
                            },
                            "required": ["examples"],
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
            return {"examples": [], "error": data.get("error", {}).get("message", "OpenAI error")}
        content = data["choices"][0]["message"]["content"].strip()
        try:
            parsed = json.loads(content)
            examples = parsed.get("examples", []) if isinstance(parsed, dict) else []
        except Exception:
            examples = []
        examples = [ex.strip() for ex in examples if isinstance(ex, str) and ex.strip()]
        return {"examples": examples, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"examples": [], "error": str(exc)}


@tools_bp.route("/missing-usage-examples/manual", methods=["GET", "POST"])
def missing_usage_examples_manual():
    storage = get_storage()
    refs_raw = request.values.get("refs") or "[]"
    target_language = (request.values.get("target_language") or "").strip().lower()
    selected_refs = [r.strip() for r in (request.form.getlist("selected_ref") or []) if r.strip()]
    action = (request.form.get("action") or "").strip()

    refs = _parse_refs(refs_raw)
    glosses = []
    seen: set[str] = set()
    if target_language:
        for ref in refs:
            if ref in seen:
                continue
            seen.add(ref)
            gloss = storage.resolve_reference(ref)
            if gloss and should_add_usage_examples(gloss, target_language):
                glosses.append(gloss)

    if request.method == "POST":
        if action == "mark_impossible":
            for ref in selected_refs:
                gloss = storage.resolve_reference(ref)
                if gloss:
                    logs = gloss.logs if isinstance(getattr(gloss, "logs", {}), dict) else {}
                    logs[datetime.utcnow().isoformat() + "Z"] = f"{USAGE_IMPOSSIBLE_MARKER}:{target_language}"
                    gloss.logs = logs
                    storage.save_gloss(gloss)
            return redirect(url_for("tools.missing_usage_examples_manual", refs=refs_raw, target_language=target_language))
        elif action == "add_manual":
            content = (request.form.get("content") or "").strip()
            base_ref = request.form.get("base_ref") or ""
            base = storage.resolve_reference(base_ref)
            if content and base and should_add_usage_examples(base, target_language):
                ex_gloss = storage.ensure_gloss(base.language, content)
                attach_relation(storage, base, "usage_examples", ex_gloss)
                flash("Usage example added.", "success")
            return redirect(url_for("tools.missing_usage_examples_manual", refs=refs_raw, target_language=target_language))

    return render_template(
        "tool_missing_usage_examples/manual.html",
        glosses=glosses,
        refs_json=refs_raw,
        target_language=target_language,
    )


@tools_bp.route("/missing-usage-examples/input", methods=["GET"])
def missing_usage_examples_input():
    refs_raw = request.values.get("refs") or "[]"
    target_language = (request.values.get("target_language") or "").strip().lower()
    languages = get_language_store().list_languages()
    return render_template(
        "tool_missing_usage_examples/input_form.html",
        refs_json=refs_raw,
        target_language=target_language,
        provider_model="OpenAI|gpt-4o-mini",
        context="",
        languages=languages,
    )


@tools_bp.route("/missing-usage-examples/output", methods=["GET", "POST"])
def missing_usage_examples_output():
    storage = get_storage()
    refs_raw = request.values.get("refs") or "[]"
    target_language = (request.values.get("target_language") or "").strip().lower()
    action = (request.form.get("action") or "").strip()
    selected_refs = [r.strip() for r in (request.form.getlist("selected_ref") or []) if r.strip()]
    selected_examples = [t for t in (request.form.getlist("selected_example") or []) if t.strip()]
    provider_model = request.form.get("provider_model") or "OpenAI|gpt-4o-mini"
    context = request.form.get("context") or ""
    results_raw = request.form.get("results_json") or "[]"

    try:
        ai_results = json.loads(results_raw)
    except Exception:
        ai_results = []

    ai_error = None
    ai_message = None
    refs = _parse_refs(refs_raw)

    glosses: list = []
    seen: set[str] = set()
    if target_language:
        for ref in refs:
            if ref in seen:
                continue
            seen.add(ref)
            gloss = storage.resolve_reference(ref)
            if gloss and should_add_usage_examples(gloss, target_language):
                glosses.append(gloss)

    settings = current_app.extensions["settings_store"].load()
    provider, model = provider_model.split("|", 1)

    if request.method == "POST":
        if not target_language:
            ai_error = "target_language is required."
        elif action == "mark_impossible":
            for ref in selected_refs:
                gloss = storage.resolve_reference(ref)
                if gloss:
                    logs = gloss.logs if isinstance(getattr(gloss, "logs", {}), dict) else {}
                    logs[datetime.utcnow().isoformat() + "Z"] = f"{USAGE_IMPOSSIBLE_MARKER}:{target_language}"
                    gloss.logs = logs
                    storage.save_gloss(gloss)
            glosses = [g for g in glosses if should_add_usage_examples(g, target_language)]
        elif action == "ai_generate":
            if not selected_refs:
                ai_error = "Select glosses to generate examples for."
            elif provider != "OpenAI":
                ai_error = "Only OpenAI is supported for now."
            elif not settings.api_keys.openai:
                ai_error = "OpenAI API key missing. Add it in Settings."
            else:
                ai_results = []
                for ref in selected_refs:
                    gloss = storage.resolve_reference(ref)
                    if not gloss or not should_add_usage_examples(gloss, target_language):
                        continue
                    result = generate_usage_examples(gloss, model, settings.api_keys.openai, context, get_language_store())
                    ai_results.append({
                        "ref": f"{gloss.language}:{gloss.slug}",
                        "content": gloss.content,
                        "language": gloss.language,
                        "examples": result.get("examples") or [],
                        "error": result.get("error"),
                    })
                if not ai_results:
                    ai_error = "No eligible glosses found to generate examples."
        elif action in ("ai_accept_all", "ai_accept_selection"):
            if not ai_results:
                ai_error = "No AI results to accept."
            else:
                added = 0
                selection_map: dict[str, list[str]] = {}
                if action == "ai_accept_selection":
                    for val in selected_examples:
                        try:
                            entry = json.loads(val)
                        except Exception:
                            continue
                        if not isinstance(entry, dict):
                            continue
                        ref = entry.get("ref")
                        example = entry.get("example")
                        if not ref or not isinstance(example, str):
                            continue
                        selection_map.setdefault(ref, []).append(example)
                for item in ai_results:
                    ref = item.get("ref", "")
                    gloss = storage.resolve_reference(ref)
                    if not gloss:
                        continue
                    examples = item.get("examples") or []
                    chosen = examples if action == "ai_accept_all" else selection_map.get(ref, [])
                    for ex_text in chosen:
                        ex_text = ex_text.strip()
                        if not ex_text:
                            continue
                        ex_gloss = storage.ensure_gloss(gloss.language, ex_text)
                        attach_relation(storage, gloss, "usage_examples", ex_gloss)
                        added += 1
                ai_results = []
                ai_message = f"Added {added} usage examples." if added else "No usage examples added."
        elif action == "ai_discard":
            ai_results = []

    ai_results_json = json.dumps(ai_results)
    return render_template(
        "tool_missing_usage_examples/output_form.html",
        glosses=glosses,
        refs_json=refs_raw,
        provider_model=provider_model,
        context=context,
        ai_results=ai_results,
        ai_results_json=ai_results_json,
        ai_error=ai_error,
        ai_message=ai_message,
        target_language=target_language,
    )

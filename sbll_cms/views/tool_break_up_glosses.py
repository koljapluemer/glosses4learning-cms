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


def _parse_refs_raw(raw: str) -> list[str]:
    try:
        parsed = json.loads(raw)
    except Exception:
        return []
    return [r.strip() for r in parsed if isinstance(r, str) and r.strip()]


def _fallback_parts_refs(storage, situation) -> list[str]:
    """Fallback: walk direct children of situation and pick glosses that should be split."""
    refs: list[str] = []
    seen: set[str] = set()
    for ref in getattr(situation, "children", []) or []:
        if ref in seen:
            continue
        seen.add(ref)
        gloss = storage.resolve_reference(ref)
        if gloss and should_break_up(gloss):
            refs.append(ref)
    return refs


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


@tools_bp.route("/break-up-glosses/<language>/<slug>/input", methods=["GET"])
def break_up_glosses_input(language: str, slug: str):
    from sbll_cms.situations_logic import collect_situation_stats

    storage = get_storage()
    situation = storage.find_gloss_by_slug(language, slug)
    if not situation:
        flash("Situation not found.", "error")
        return redirect(url_for("situations.list_situations"))

    native_language = request.args.get("native_language", "")
    target_language = request.args.get("target_language", "")

    # Load refs dynamically from situation stats
    stats = collect_situation_stats(storage, situation, native_language, target_language)
    refs = list(stats.get("parts_missing", set()))

    print(f"\n=== BREAK UP GLOSSES INPUT DEBUG ===")
    print(f"Situation: {language}:{slug}")
    print(f"Native: {native_language}, Target: {target_language}")
    print(f"Loaded {len(refs)} refs from situation stats")
    print(f"=== END INPUT DEBUG ===\n")

    return render_template(
        "tool_break_up_glosses/input_form.html",
        situation=situation,
        native_language=native_language,
        target_language=target_language,
        refs_json=json.dumps(refs),
        provider_model="OpenAI|gpt-4o-mini",
        context="",
    )


@tools_bp.route("/break-up-glosses/<language>/<slug>/output", methods=["GET", "POST"])
def break_up_glosses_output(language: str, slug: str):
    from sbll_cms.situations_logic import collect_situation_stats

    storage = get_storage()
    situation = storage.find_gloss_by_slug(language, slug)
    if not situation:
        flash("Situation not found.", "error")
        return redirect(url_for("situations.list_situations"))

    json_mode = request.method == "POST" and request.is_json
    refs_raw = request.values.get("refs") or "[]"

    if json_mode:
        payload = request.get_json(force=True) or {}
        provider_model = payload.get("provider_model") or "OpenAI|gpt-4o-mini"
        context_text = payload.get("context") or ""
        results_raw = json.dumps(payload.get("results") or [])
        action = (payload.get("mode") or payload.get("action") or "").strip()
        selected_refs = [r.strip() for r in (payload.get("selected_refs") or []) if isinstance(r, str) and r.strip()]
        selected_parts = []
        for entry in payload.get("selections", []):
            if not isinstance(entry, dict):
                continue
            ref = (entry.get("ref") or "").strip()
            part = (entry.get("value") or "").strip()
            if ref and part:
                selected_parts.append(json.dumps({"ref": ref, "part": part}))
        native_language = payload.get("native_language", "")
        target_language = payload.get("target_language", "")
    else:
        provider_model = request.args.get("provider_model") or "OpenAI|gpt-4o-mini"
        context_text = request.args.get("context") or ""
        results_raw = "[]"
        action = ""
        selected_parts = []
        selected_refs = []
        native_language = request.args.get("native_language", "")
        target_language = request.args.get("target_language", "")

    if "|" in provider_model:
        provider, model = provider_model.split("|", 1)
    else:
        provider, model = provider_model, ""

    # Load refs dynamically from situation stats; fallback to provided refs if stats empty
    stats = collect_situation_stats(storage, situation, native_language, target_language)
    refs = list(stats.get("parts_missing", set()))
    if not refs:
        refs = _parse_refs_raw(refs_raw)
    if not refs:
        refs = _fallback_parts_refs(storage, situation)

    print(f"\n=== BREAK UP GLOSSES OUTPUT DEBUG ===")
    print(f"Method: {request.method}")
    print(f"Situation: {language}:{slug}")
    print(f"Loaded {len(refs)} refs from situation stats")
    print(f"Refs_raw count: {len(_parse_refs_raw(refs_raw))}")
    print(f"Fallback refs count: {len(_fallback_parts_refs(storage, situation))}")
    print(f"native_language={native_language}, target_language={target_language}")
    print(f"provider_model: {provider_model}")
    print(f"context_text: {context_text}")
    print(f"action: {action}")

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
        print(f"  Ref {ref}: gloss={gloss.content if gloss else None}, should_break_up={should_break_up(gloss) if gloss else None}")
        if gloss and should_break_up(gloss):
            glosses.append(gloss)

    print(f"Total glosses to process: {len(glosses)}")
    print(f"=== END DEBUG ===\n")

    if json_mode:
        if action in ("generate", "ai_generate"):
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
        elif action in ("ai_accept_all", "ai_accept_selection", "accept_all", "accept_selection"):
            if not ai_results:
                ai_error = "No AI results to accept."
            else:
                added = 0
                selection_map: dict[str, list[str]] = {}
                if action in ("ai_accept_selection", "accept_selection"):
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
                    chosen = parts if action in ("ai_accept_all", "accept_all") else selection_map.get(ref, [])
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

    if json_mode:
        status = 200 if not ai_error else 400
        return {
            "ai_results": ai_results,
            "ai_error": ai_error,
            "ai_message": ai_message,
        }, status

    return render_template(
        "tool_break_up_glosses/output_form.html",
        language=language,
        slug=slug,
        glosses=glosses,
        refs_json=json.dumps(refs),
        provider_model=provider_model,
        context=context_text,
        native_language=native_language,
        target_language=target_language,
    )

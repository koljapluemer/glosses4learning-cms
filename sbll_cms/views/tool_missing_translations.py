from __future__ import annotations

import json
from datetime import datetime

from flask import current_app, flash, redirect, render_template, request, url_for

from sbll_cms.entities.gloss import Gloss, attach_relation
from sbll_cms.entities.language import get_language_store
from sbll_cms.storage import get_storage
from sbll_cms.translation_tool import TranslationRequest, translate
from sbll_cms.views.blueprints import tools_bp

TRANSLATION_IMPOSSIBLE_MARKER = "TRANSLATION_CONSIDERED_IMPOSSIBLE"


def should_translate_missing(gloss, native_language: str, target_language: str) -> bool:
    if gloss.language != target_language:
        return False
    tags = gloss.tags or []
    if "eng:paraphrase" in tags:
        return False
    translations = gloss.translations or []
    has_native = any(ref.startswith(f"{native_language}:") for ref in translations)
    if has_native:
        return False
    logs = getattr(gloss, "logs", {}) or {}
    if isinstance(logs, dict):
        blocked = any(f"{TRANSLATION_IMPOSSIBLE_MARKER}:{native_language}" in str(val) for val in logs.values())
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


@tools_bp.route("/missing-translations/manual", methods=["GET", "POST"])
def missing_translations_manual():
    storage = get_storage()
    refs_raw = request.values.get("refs") or "[]"
    native_language = (request.values.get("native_language") or "").strip().lower()
    target_language = (request.values.get("target_language") or "").strip().lower()
    selected_refs = [r.strip() for r in (request.form.getlist("selected_ref") or []) if r.strip()]
    action = (request.form.get("action") or "").strip()

    refs = _parse_refs(refs_raw)
    glosses = []
    seen: set[str] = set()
    if native_language and target_language:
        for ref in refs:
            if ref in seen:
                continue
            seen.add(ref)
            gloss = storage.resolve_reference(ref)
            if gloss and should_translate_missing(gloss, native_language, target_language):
                glosses.append(gloss)

    if request.method == "POST" and action == "mark_impossible":
        for ref in selected_refs:
            gloss = storage.resolve_reference(ref)
            if gloss:
                logs = gloss.logs if isinstance(getattr(gloss, "logs", {}), dict) else {}
                logs[datetime.utcnow().isoformat() + "Z"] = f"{TRANSLATION_IMPOSSIBLE_MARKER}:{native_language}"
                gloss.logs = logs
                storage.save_gloss(gloss)
        return redirect(url_for("tools.missing_translations_manual", refs=refs_raw, native_language=native_language, target_language=target_language))

    return render_template(
        "tool_missing_translations/manual.html",
        glosses=glosses,
        refs_json=refs_raw,
        native_language=native_language,
        target_language=target_language,
    )


@tools_bp.route("/missing-translations/input", methods=["GET"])
def missing_translations_input():
    refs_raw = request.values.get("refs") or "[]"
    native_language = (request.values.get("native_language") or "").strip().lower()
    target_language = (request.values.get("target_language") or "").strip().lower()
    languages = get_language_store().list_languages()
    return render_template(
        "tool_missing_translations/input_form.html",
        refs_json=refs_raw,
        native_language=native_language,
        target_language=target_language,
        provider_model="OpenAI|gpt-4o-mini",
        context="",
        languages=languages,
    )


@tools_bp.route("/missing-translations/output", methods=["GET", "POST"])
def missing_translations_output():
    storage = get_storage()
    json_mode = request.method == "POST" and request.is_json

    if json_mode:
        payload = request.get_json(force=True) or {}
        refs_raw = json.dumps(payload.get("refs") or [])
        native_language = (payload.get("native_language") or "").strip().lower()
        target_language = (payload.get("target_language") or "").strip().lower()
        action = (payload.get("mode") or payload.get("action") or "").strip()
        selected_refs = [r.strip() for r in (payload.get("selected_refs") or []) if isinstance(r, str) and r.strip()]
        selected_translations = []
        for entry in payload.get("selections", []):
            if not isinstance(entry, dict):
                continue
            ref = (entry.get("ref") or "").strip()
            translation = (entry.get("value") or "").strip()
            if ref and translation:
                selected_translations.append(json.dumps({"ref": ref, "translation": translation}))
        provider_model = payload.get("provider_model") or "OpenAI|gpt-4o-mini"
        context = payload.get("context") or ""
        results_raw = json.dumps(payload.get("results") or [])
    else:
        refs_raw = request.values.get("refs") or "[]"
        native_language = (request.values.get("native_language") or "").strip().lower()
        target_language = (request.values.get("target_language") or "").strip().lower()
        action = ""
        selected_refs = [r.strip() for r in (request.form.getlist("selected_ref") or []) if r.strip()]
        selected_translations = [t for t in (request.form.getlist("selected_translation") or []) if t.strip()]
        provider_model = request.values.get("provider_model") or "OpenAI|gpt-4o-mini"
        context = request.values.get("context") or ""
        results_raw = request.values.get("results_json") or "[]"

    try:
        ai_results = json.loads(results_raw)
    except Exception:
        ai_results = []

    ai_error = None
    ai_message = None
    refs = _parse_refs(refs_raw)

    glosses: list = []
    seen: set[str] = set()
    if native_language and target_language:
        for ref in refs:
            if ref in seen:
                continue
            seen.add(ref)
            gloss = storage.resolve_reference(ref)
            if gloss and should_translate_missing(gloss, native_language, target_language):
                glosses.append(gloss)

    settings = current_app.extensions["settings_store"].load()
    if "|" in provider_model:
        provider, model = provider_model.split("|", 1)
    else:
        provider, model = provider_model, ""

    if json_mode:
        if not native_language or not target_language:
            ai_error = "Both native_language and target_language are required."
        elif action in ("mark_impossible",):
            for ref in selected_refs:
                gloss = storage.resolve_reference(ref)
                if gloss:
                    logs = gloss.logs if isinstance(getattr(gloss, "logs", {}), dict) else {}
                    logs[datetime.utcnow().isoformat() + "Z"] = f"{TRANSLATION_IMPOSSIBLE_MARKER}:{native_language}"
                    gloss.logs = logs
                    storage.save_gloss(gloss)
            glosses = [g for g in glosses if should_translate_missing(g, native_language, target_language)]
        elif action in ("ai_generate", "generate"):
            if not selected_refs:
                ai_error = "Select glosses to translate."
            elif provider != "OpenAI":
                ai_error = "Only OpenAI is supported for now."
            elif not settings.api_keys.openai:
                ai_error = "OpenAI API key missing. Add it in Settings."
            else:
                ai_results = []
                for ref in selected_refs:
                    gloss = storage.resolve_reference(ref)
                    if not gloss or not should_translate_missing(gloss, native_language, target_language):
                        continue
                    req = TranslationRequest(
                        gloss=gloss,
                        target_language=native_language,
                        provider=provider,
                        model=model,
                        context=context,
                    )
                    result = translate(req, settings, get_language_store())
                    ai_results.append({
                        "ref": f"{gloss.language}:{gloss.slug}",
                        "content": gloss.content,
                        "language": gloss.language,
                        "translations": result.translations or [],
                        "error": result.error,
                    })
                if not ai_results:
                    ai_error = "No eligible glosses found to translate."
        elif action in ("ai_accept_all", "ai_accept_selection", "accept_all", "accept_selection"):
            if not ai_results:
                ai_error = "No AI results to accept."
            else:
                added = 0
                selection_map: dict[str, list[str]] = {}
                if action in ("ai_accept_selection", "accept_selection"):
                    for val in selected_translations:
                        try:
                            entry = json.loads(val)
                        except Exception:
                            continue
                        if not isinstance(entry, dict):
                            continue
                        ref = entry.get("ref")
                        translation = entry.get("translation")
                        if not ref or not isinstance(translation, str):
                            continue
                        selection_map.setdefault(ref, []).append(translation)
                for item in ai_results:
                    ref = item.get("ref", "")
                    gloss = storage.resolve_reference(ref)
                    if not gloss:
                        continue
                    translations = item.get("translations") or []
                    chosen = translations if action in ("ai_accept_all", "accept_all") else selection_map.get(ref, [])
                    for t_text in chosen:
                        t_text = t_text.strip()
                        if not t_text:
                            continue
                        target = storage.ensure_gloss(native_language, t_text)
                        attach_relation(storage, gloss, "translations", target)
                        added += 1
                ai_results = []
                ai_message = f"Added {added} translations." if added else "No translations added."
        elif action in ("ai_discard", "discard"):
            ai_results = []

    if json_mode:
        status = 200 if not ai_error else 400
        return {
            "ai_results": ai_results,
            "ai_error": ai_error,
            "ai_message": ai_message,
        }, status

    return render_template(
        "tool_missing_translations/output_form.html",
        glosses=glosses,
        refs_json=refs_raw,
        provider_model=provider_model,
        context=context,
        native_language=native_language,
        target_language=target_language,
    )

from __future__ import annotations

import json

from flask import current_app, flash, redirect, render_template, request, url_for

from sbll_cms.entities.gloss import Gloss, attach_relation, detach_relation
from sbll_cms.entities.language import get_language_store
from sbll_cms.storage import get_storage
from sbll_cms.translation_tool import TranslationRequest, translate
from sbll_cms.views.blueprints import tools_bp


def _load_context(language: str, slug: str):
    storage = get_storage()
    gloss = storage.load_gloss(language, slug)
    if not gloss:
        return None, storage
    languages = get_language_store().list_languages()
    return (gloss, languages), storage


@tools_bp.route("/translation/<language>/<slug>/input", methods=["GET"])
def translation_tool_input(language: str, slug: str):
    ctx, _storage = _load_context(language, slug)
    if not ctx:
        flash("Gloss not found.", "error")
        return redirect(url_for("glosses.index")), 404
    gloss, languages = ctx
    other_langs = [lang for lang in languages if lang.iso_code != gloss.language]
    return render_template(
        "tool_translation/input_form.html",
        gloss=gloss,
        languages=other_langs,
        provider_model="OpenAI|gpt-4o-mini",
        context="",
    )


@tools_bp.route("/translation/<language>/<slug>/output", methods=["GET", "POST"])
def translation_tool_output(language: str, slug: str):
    ctx, storage = _load_context(language, slug)
    if not ctx:
        flash("Gloss not found.", "error")
        return redirect(url_for("glosses.index")), 404
    gloss, languages = ctx
    other_langs = [lang for lang in languages if lang.iso_code != gloss.language]

    provider_model = request.form.get("provider_model", "OpenAI|gpt-4o-mini")
    if "|" in provider_model:
        provider, model = provider_model.split("|", 1)
    else:
        provider, model = provider_model, ""

    target_language = request.form.get("target_language") or (other_langs[0].iso_code if other_langs else "")
    context_text = request.form.get("context") or ""
    action = request.form.get("action") or "generate"
    translations_json = request.form.get("translations_json") or ""
    selected_refs = request.form.getlist("selected_translation")
    try:
        translations_list = json.loads(translations_json) if translations_json else []
    except Exception:  # noqa: BLE001
        translations_list = []
    translations_list = [t.strip() for t in translations_list if t and t.strip()]

    settings = current_app.extensions["settings_store"].load()

    error = None
    message = None
    result = None

    try:
        if request.method == "POST":
            if not other_langs:
                error = "No target languages configured. Add another language in Settings first."
            elif action in ("accept_all", "accept_selection", "discard_all"):
                if action != "discard_all" and not translations_list:
                    error = "No translation text to process."
                elif not target_language:
                    error = "Target language missing."
                else:
                    to_accept = translations_list if action == "accept_all" else [t for t in translations_list if t in selected_refs]
                    if action == "discard_all":
                        message = "Discarded."
                    elif not to_accept:
                        error = "No translations selected."
                    else:
                        for t_text in to_accept:
                            existing = storage.find_gloss_by_content(target_language, t_text)
                            if existing:
                                target = existing
                            else:
                                target = storage.create_gloss(Gloss(content=t_text, language=target_language, tags=["machine-translation"]))
                            attach_relation(storage, gloss, "translations", target)
                        message = "Translations added."
                    translations_list = []
                    result = None
            else:
                if not target_language:
                    error = "Select a target language."
                elif not settings or not settings.api_keys.openai:
                    error = "OpenAI API key missing. Add it in Settings."
                else:
                    req = TranslationRequest(
                        gloss=gloss,
                        target_language=target_language,
                        provider=provider,
                        model=model,
                        context=context_text,
                    )
                    result = translate(req, settings, get_language_store())
                    if result.error:
                        error = result.error
                        result = None
                    else:
                        translations_list = result.translations or []
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
        result = None

    return render_template(
        "tool_translation/output_form.html",
        gloss=storage.load_gloss(gloss.language, gloss.slug) or gloss,
        languages=other_langs,
        result=result,
        error=error,
        message=message,
        target_language=target_language,
        provider_model=provider_model,
        context=context_text,
        translations_list=translations_list,
    )


@tools_bp.route("/translation/<language>/<slug>/manual", methods=["GET", "POST"])
def translation_tool_manual(language: str, slug: str):
    ctx, storage = _load_context(language, slug)
    if not ctx:
        flash("Gloss not found.", "error")
        return redirect(url_for("glosses.index")), 404
    gloss, languages = ctx
    other_langs = [lang for lang in languages if lang.iso_code != gloss.language]

    target_language = request.form.get("target_language") or (other_langs[0].iso_code if other_langs else "")
    content = (request.form.get("content") or "").strip()
    action = request.form.get("action") or ""
    detach_ref = request.form.get("detach_ref") or ""

    message = None
    error = None

    if request.method == "POST":
        if action == "add":
            if not target_language or not content:
                error = "Target language and content are required."
            else:
                target = storage.ensure_gloss(target_language, content)
                attach_relation(storage, gloss, "translations", target)
                message = "Translation added."
        elif action == "detach" and detach_ref:
            detach_relation(storage, gloss, "translations", detach_ref)
            message = "Translation detached."

    translations = []
    for ref in gloss.translations or []:
        t = storage.resolve_reference(ref)
        if t:
            translations.append((ref, t))

    return render_template(
        "tool_translation/manual.html",
        gloss=storage.load_gloss(gloss.language, gloss.slug) or gloss,
        languages=other_langs,
        target_language=target_language,
        translations=translations,
        message=message,
        error=error,
    )

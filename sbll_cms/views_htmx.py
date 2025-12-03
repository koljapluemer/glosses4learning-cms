from __future__ import annotations

from flask import Blueprint, abort, render_template, request
import json

from .gloss import RELATIONSHIP_FIELDS, Gloss
from .constants import WITHIN_LANGUAGE_RELATIONS, CROSS_LANGUAGE_RELATIONS
from .language import get_language_store
from .relations import attach_relation, detach_relation
from .storage import get_storage
from .translation_tool import TranslationRequest, translate
from .settings import Settings
from flask import current_app
from .utils import normalize_language_code

bp = Blueprint("htmx", __name__)


def _load_base(language: str, slug: str):
    storage = get_storage()
    base = storage.load_gloss(language, slug)
    if not base:
        abort(404)
    return base


def _relation_rows(base, field):
    storage = get_storage()
    rows = []
    for ref in getattr(base, field):
        if ":" in ref:
            iso, slug = ref.split(":", 1)
        else:
            iso, slug = base.language, ref
        related = storage.resolve_reference(ref)
        tags = related.tags if related else []
        rows.append(
            {
                "ref": ref,
                "iso": iso,
                "slug": slug,
                "title": related.content if related else slug,
                "tags": tags,
            }
        )
    return rows


@bp.get("/glosses/<language>/<slug>/relations/<field>")
def relation_table(language: str, slug: str, field: str):
    if field not in RELATIONSHIP_FIELDS:
        abort(400)
    base = _load_base(language, slug)
    rows = _relation_rows(base, field)
    languages = get_language_store().list_languages()
    return render_template(
        "partials/relation_table.html",
        base=base,
        field=field,
        rows=rows,
        languages=languages,
        allow_language_select=field in CROSS_LANGUAGE_RELATIONS,
        message=None,
        error=None,
    )


@bp.post("/glosses/<language>/<slug>/relations/<field>/add")
def add_relation(language: str, slug: str, field: str):
    if field not in RELATIONSHIP_FIELDS:
        abort(400)
    base = _load_base(language, slug)
    storage = get_storage()

    target_ref = request.form.get("target_ref") or ""
    target_iso_raw = request.form.get("target_iso") or (base.language if field in WITHIN_LANGUAGE_RELATIONS else None)
    try:
        target_iso = normalize_language_code(target_iso_raw)
    except ValueError as exc:
        error = str(exc)
        target_iso = None
    target_content = (request.form.get("target_content") or "").strip()

    error = None
    if target_ref:
        target = storage.resolve_reference(target_ref)
        if not target:
            error = "Related gloss not found."
    else:
        if not target_content:
            error = "Content is required to add a relation."
        else:
            try:
                target = storage.ensure_gloss(target_iso, target_content)
            except ValueError as exc:
                error = str(exc)
            except FileExistsError:
                target = storage.find_gloss_by_content(target_iso, target_content)

    if not error:
        attach_relation(storage, base, field, target)
        # If base uses target as usage example, ensure reverse part link.
        if field == "usage_examples":
            base_ref = f"{base.language}:{base.slug}"
            if base_ref not in (target.parts or []):
                target.parts.append(base_ref)
                storage.save_gloss(target)
        message = "Relation added."
    else:
        message = None

    rows = _relation_rows(base, field)
    languages = get_language_store().list_languages()
    return render_template(
        "partials/relation_table.html",
        base=storage.load_gloss(base.language, base.slug) or base,
        field=field,
        rows=rows,
        languages=languages,
        allow_language_select=field in CROSS_LANGUAGE_RELATIONS,
        message=message,
        error=error,
    )


@bp.post("/glosses/<language>/<slug>/relations/<field>/detach")
def remove_relation(language: str, slug: str, field: str):
    if field not in RELATIONSHIP_FIELDS:
        abort(400)
    base = _load_base(language, slug)
    storage = get_storage()
    target_ref = request.form.get("target_ref") or ""
    if target_ref:
        detach_relation(storage, base, field, target_ref)
    rows = _relation_rows(base, field)
    languages = get_language_store().list_languages()
    return render_template(
        "partials/relation_table.html",
        base=storage.load_gloss(base.language, base.slug) or base,
        field=field,
        rows=rows,
        languages=languages,
        allow_language_select=field in CROSS_LANGUAGE_RELATIONS,
        message="Relation removed.",
        error=None,
    )


@bp.get("/glosses/suggest")
def suggest_glosses():
    query = request.args.get("q", "") or request.args.get("target_content", "")
    language_filter = request.args.get("target_iso") or request.args.get("language")
    field = request.args.get("field")
    base_language = request.args.get("base_language")
    base_slug = request.args.get("base_slug")
    if not field or not base_language or not base_slug:
        abort(400)
    if field in WITHIN_LANGUAGE_RELATIONS:
        language_filter = base_language

    storage = get_storage()
    results = storage.search_glosses(query, language_filter)
    action_url = (
        f"/htmx/glosses/{base_language}/{base_slug}/relations/{field}/add"
    )
    target_id = f"relation-{field}"
    return render_template(
        "partials/suggestions.html",
        results=results,
        action_url=action_url,
        target_id=target_id,
    )


def _require_keys(provider: str, settings: Settings):
    return bool(settings.api_keys.openai)


@bp.route("/glosses/<language>/<slug>/translation-tool", methods=["GET", "POST"])
def translation_tool(language: str, slug: str):
    storage = get_storage()
    gloss = storage.load_gloss(language, slug)
    if not gloss:
        abort(404)
    languages = get_language_store().list_languages()

    provider_model = request.form.get("provider_model", "OpenAI|gpt-4o-mini")
    provider, model = provider_model.split("|", 1)
    target_language = request.form.get("target_language")
    context = request.form.get("context") or ""
    action = request.form.get("action") or "generate"
    translations_json = request.form.get("translations_json") or ""
    selected_refs = request.form.getlist("selected_translation")
    try:
        translations_list = json.loads(translations_json) if translations_json else []
    except Exception:
        translations_list = []
    translations_list = [t.strip() for t in translations_list if t and t.strip()]

    settings_store = current_app.extensions["settings_store"]
    settings = settings_store.load()

    error = None
    message = None
    result = None

    try:
        if request.method == "POST":
            if action in ("accept_all", "accept_selection", "discard_all"):
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
                        from .relations import attach_relation

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
                # generate
                if not target_language:
                    error = "Select a target language."
                elif not _require_keys(provider, settings):
                    error = f"{provider} API key missing. Add it in Settings."
                else:
                    req = TranslationRequest(
                        gloss=gloss,
                        target_language=target_language,
                        provider=provider,
                        model=model,
                        context=context,
                    )
                    result = translate(req, settings, get_language_store())
                    if result.error:
                        error = result.error
                        result = None
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
        result = None

    return render_template(
        "partials/translation_tool.html",
        gloss=storage.load_gloss(gloss.language, gloss.slug) or gloss,
        languages=languages,
        result=result,
        error=error,
        message=message,
        target_language=target_language,
        provider_model=provider_model,
        context=context,
        translations_list=translations_list,
    )

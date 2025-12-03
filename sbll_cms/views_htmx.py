from __future__ import annotations

from flask import Blueprint, abort, render_template, request

from .gloss import RELATIONSHIP_FIELDS
from .constants import WITHIN_LANGUAGE_RELATIONS, CROSS_LANGUAGE_RELATIONS
from .language import get_language_store
from .relations import attach_relation, detach_relation
from .storage import get_storage
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
        rows.append(
            {
                "ref": ref,
                "iso": iso,
                "slug": slug,
                "title": related.content if related else slug,
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
    target_iso = normalize_language_code(request.form.get("target_iso") or base.language if field in WITHIN_LANGUAGE_RELATIONS else None)
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

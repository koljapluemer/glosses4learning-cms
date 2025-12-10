from __future__ import annotations

from flask import render_template, request

from sbll_cms.entities.gloss import (
    CROSS_LANGUAGE_RELATIONS,
    attach_relation,
    gloss_relation_rows,
    load_gloss_or_404,
    require_relation_field,
)
from sbll_cms.entities.language import get_language_store
from sbll_cms.storage import get_storage
from sbll_cms.utils.normalize_language_code import normalize_language_code
from sbll_cms.views.blueprints import htmx_bp


@htmx_bp.post("/glosses/<language>/<slug>/relations/<field>/add")
def add_relation(language: str, slug: str, field: str):
    require_relation_field(field)
    base = load_gloss_or_404(language, slug)
    storage = get_storage()

    target_ref = request.form.get("target_ref") or ""
    from sbll_cms.entities.gloss import WITHIN_LANGUAGE_RELATIONS  # local import to avoid cycle
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
        if field == "usage_examples":
            base_ref = f"{base.language}:{base.slug}"
            if base_ref not in (target.parts or []):
                target.parts.append(base_ref)
                storage.save_gloss(target)
        message = "Relation added."
    else:
        message = None

    rows = gloss_relation_rows(base, field)
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

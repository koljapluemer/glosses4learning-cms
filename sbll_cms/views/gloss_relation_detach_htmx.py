from __future__ import annotations

from flask import render_template, request

from sbll_cms.entities.gloss import CROSS_LANGUAGE_RELATIONS, detach_relation, gloss_relation_rows, load_gloss_or_404, require_relation_field
from sbll_cms.entities.language import get_language_store
from sbll_cms.storage import get_storage
from sbll_cms.views.blueprints import htmx_bp


@htmx_bp.post("/glosses/<language>/<slug>/relations/<field>/detach")
def remove_relation(language: str, slug: str, field: str):
    require_relation_field(field)
    base = load_gloss_or_404(language, slug)
    storage = get_storage()
    target_ref = request.form.get("target_ref") or ""
    if target_ref:
        detach_relation(storage, base, field, target_ref)
    rows = gloss_relation_rows(base, field)
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

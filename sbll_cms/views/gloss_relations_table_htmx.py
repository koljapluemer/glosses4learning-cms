from __future__ import annotations

from flask import render_template

from sbll_cms.entities.gloss import CROSS_LANGUAGE_RELATIONS, gloss_relation_rows, load_gloss_or_404, require_relation_field
from sbll_cms.entities.language import get_language_store
from sbll_cms.views.blueprints import htmx_bp


@htmx_bp.get("/glosses/<language>/<slug>/relations/<field>")
def relation_table(language: str, slug: str, field: str):
    require_relation_field(field)
    base = load_gloss_or_404(language, slug)
    rows = gloss_relation_rows(base, field)
    languages = get_language_store().list_languages()
    lang_groups = {}
    if field == "translations":
        for row in rows:
            lang_groups.setdefault(row["iso"], 0)
            lang_groups[row["iso"]] += 1
    return render_template(
        "partials/relation_table.html",
        base=base,
        field=field,
        rows=rows,
        languages=languages,
        allow_language_select=field in CROSS_LANGUAGE_RELATIONS,
        lang_groups=lang_groups if field == "translations" else None,
        message=None,
        error=None,
    )

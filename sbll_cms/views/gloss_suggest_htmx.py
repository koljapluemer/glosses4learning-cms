from __future__ import annotations

from flask import abort, render_template, request

from sbll_cms.entities.gloss import WITHIN_LANGUAGE_RELATIONS
from sbll_cms.storage import get_storage
from sbll_cms.views.blueprints import htmx_bp


@htmx_bp.get("/glosses/suggest")
def gloss_suggest_htmx():
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
    action_url = f"/htmx/glosses/{base_language}/{base_slug}/relations/{field}/add"
    target_id = f"relation-{field}"
    return render_template(
        "partials/suggestions.html",
        results=results,
        action_url=action_url,
        target_id=target_id,
    )

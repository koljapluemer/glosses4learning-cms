from __future__ import annotations

from flask import flash, redirect, render_template, url_for

from sbll_cms.entities.gloss import RELATIONSHIP_FIELDS
from sbll_cms.entities.language import get_language_store
from sbll_cms.storage import get_storage
from sbll_cms.views.blueprints import glosses_bp


@glosses_bp.route("/glosses/<language>/<slug>/edit", methods=["GET"], endpoint="edit_gloss")
def edit_gloss(language: str, slug: str):
    storage = get_storage()
    gloss = storage.load_gloss(language, slug)
    if not gloss:
        flash("Gloss not found.", "error")
        return redirect(url_for("glosses.index")), 404
    languages = get_language_store().list_languages()
    if not languages:
        flash("No languages configured. Add a language file first.", "error")
        return redirect(url_for("glosses.index"))
    return render_template(
        "gloss_form.html",
        gloss=gloss,
        mode="edit",
        relationships=RELATIONSHIP_FIELDS,
        languages=languages,
    )

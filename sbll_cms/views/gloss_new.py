from __future__ import annotations

from flask import flash, redirect, render_template, url_for

from sbll_cms.entities.gloss import Gloss, RELATIONSHIP_FIELDS
from sbll_cms.entities.language import get_language_store
from sbll_cms.views.blueprints import glosses_bp


@glosses_bp.route("/glosses/new", methods=["GET"], endpoint="new_gloss")
def new_gloss():
    languages = get_language_store().list_languages()
    if not languages:
        flash("No languages configured. Add a language file first.", "error")
        return redirect(url_for("glosses.index"))

    default_language = next((lang.iso_code for lang in languages if lang.iso_code == "eng"), languages[0].iso_code)
    empty_gloss = Gloss(content="", language=default_language)
    return render_template(
        "gloss_form.html",
        gloss=empty_gloss,
        mode="create",
        relationships=RELATIONSHIP_FIELDS,
        languages=languages,
    )

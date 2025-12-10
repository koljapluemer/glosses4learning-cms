from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for

from sbll_cms.entities.gloss import RELATIONSHIP_FIELDS, gloss_from_request, validate_gloss
from sbll_cms.entities.language import get_language_store
from sbll_cms.storage import get_storage
from sbll_cms.views.blueprints import glosses_bp


@glosses_bp.route("/glosses", methods=["POST"], endpoint="create_gloss")
def create_gloss():
    gloss = gloss_from_request(request)
    languages = get_language_store().list_languages()
    next_action = request.form.get("next_action") or "stay"
    errors = validate_gloss(gloss)
    if errors:
        for message in errors:
            flash(message, "error")
        return (
            render_template(
                "gloss_form.html",
                gloss=gloss,
                mode="create",
                relationships=RELATIONSHIP_FIELDS,
                languages=languages,
            ),
            400,
        )

    storage = get_storage()
    try:
        saved = storage.create_gloss(gloss)
    except FileExistsError as exc:
        flash(str(exc), "error")
        return (
            render_template(
                "gloss_form.html",
                gloss=gloss,
                mode="create",
                relationships=RELATIONSHIP_FIELDS,
                languages=languages,
            ),
            409,
        )
    except ValueError as exc:  # noqa: BLE001
        flash(str(exc), "error")
        return (
            render_template(
                "gloss_form.html",
                gloss=gloss,
                mode="create",
                relationships=RELATIONSHIP_FIELDS,
                languages=languages,
            ),
            400,
        )

    flash("Gloss created.", "success")
    if next_action == "list":
        return redirect(url_for("glosses.index"))
    if next_action == "add_another":
        return redirect(url_for("glosses.new_gloss"))
    return redirect(url_for("glosses.edit_gloss", language=saved.language, slug=saved.slug))

from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for

from sbll_cms.entities.gloss import RELATIONSHIP_FIELDS, gloss_from_request, validate_gloss
from sbll_cms.entities.language import get_language_store
from sbll_cms.storage import get_storage
from sbll_cms.views.blueprints import glosses_bp


@glosses_bp.route("/glosses/<language>/<slug>", methods=["POST"], endpoint="update_gloss")
def update_gloss(language: str, slug: str):
    storage = get_storage()
    current = storage.load_gloss(language, slug)
    if not current:
        flash("Gloss not found.", "error")
        return redirect(url_for("glosses.index")), 404

    updated = gloss_from_request(request)
    for rel_field in RELATIONSHIP_FIELDS:
        setattr(updated, rel_field, getattr(current, rel_field))
    languages = get_language_store().list_languages()
    next_action = request.form.get("next_action") or "stay"
    errors = validate_gloss(updated)
    if errors:
        for message in errors:
            flash(message, "error")
        return (
            render_template(
                "gloss_form.html",
                gloss=updated,
                mode="edit",
                relationships=RELATIONSHIP_FIELDS,
                languages=languages,
            ),
            400,
        )

    try:
        saved = storage.update_gloss(language, slug, updated)
    except FileExistsError as exc:
        flash(str(exc), "error")
        return (
            render_template(
                "gloss_form.html",
                gloss=updated,
                mode="edit",
                relationships=RELATIONSHIP_FIELDS,
                languages=languages,
            ),
            409,
        )
    except (ValueError, FileNotFoundError) as exc:  # noqa: BLE001
        flash(str(exc), "error")
        return (
            render_template(
                "gloss_form.html",
                gloss=updated,
                mode="edit",
                relationships=RELATIONSHIP_FIELDS,
                languages=languages,
            ),
            400,
        )

    flash("Gloss updated.", "success")
    if next_action == "list":
        return redirect(url_for("glosses.index"))
    if next_action == "add_another":
        return redirect(url_for("glosses.new_gloss"))
    return redirect(url_for("glosses.edit_gloss", language=saved.language, slug=saved.slug))

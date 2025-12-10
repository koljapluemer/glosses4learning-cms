from __future__ import annotations

from flask import flash, redirect, url_for

from sbll_cms.storage import get_storage
from sbll_cms.views.blueprints import glosses_bp


@glosses_bp.route("/glosses/<language>/<slug>/delete", methods=["POST"], endpoint="delete_gloss")
def delete_gloss(language: str, slug: str):
    storage = get_storage()
    storage.delete_gloss(language, slug)
    flash("Gloss deleted.", "success")
    return redirect(url_for("glosses.index"))

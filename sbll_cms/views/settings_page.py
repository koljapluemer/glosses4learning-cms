from __future__ import annotations

from flask import current_app, flash, redirect, render_template, request, url_for

from sbll_cms.entities.gloss import Gloss  # noqa: F401  # kept for template context hints if needed
from sbll_cms.settings import ApiKeys, Settings
from sbll_cms.views.blueprints import settings_bp


@settings_bp.route("/", methods=["GET", "POST"])
def settings_page():
    store = current_app.extensions["settings_store"]
    current = store.load()
    if request.method == "POST":
        openai = (request.form.get("openai") or "").strip() or None
        deepl = (request.form.get("deepl") or "").strip() or None
        current.api_keys = ApiKeys(openai=openai, deepl=deepl)
        store.save(current)
        flash("Settings saved.", "success")
        return redirect(url_for("settings.settings_page"))
    return render_template("settings.html", settings=current)

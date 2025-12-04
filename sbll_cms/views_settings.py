from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for, current_app, jsonify

from .settings import Settings, ApiKeys

bp = Blueprint("settings", __name__)


@bp.route("/", methods=["GET", "POST"])
def settings():
    store = current_app.extensions["settings_store"]
    current = store.load()
    if request.method == "POST":
        openai = (request.form.get("openai") or "").strip() or None
        deepl = (request.form.get("deepl") or "").strip() or None
        current.api_keys = ApiKeys(openai=openai, deepl=deepl)
        store.save(current)
        flash("Settings saved.", "success")
        return redirect(url_for("settings.settings"))
    return render_template("settings.html", settings=current)


@bp.route("/api", methods=["GET"])
def get_settings():
    store = current_app.extensions["settings_store"]
    current = store.load()
    return jsonify(current.to_dict())


@bp.route("/api", methods=["POST"])
def update_settings():
    store = current_app.extensions["settings_store"]
    data = request.get_json()
    if data and "api_keys" in data:
        api_keys_data = data["api_keys"]
        openai = api_keys_data.get("openai")
        deepl = api_keys_data.get("deepl")
        current = Settings(api_keys=ApiKeys(openai=openai, deepl=deepl))
        store.save(current)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Invalid data"}), 400

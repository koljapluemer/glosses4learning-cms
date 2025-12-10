from __future__ import annotations

from flask import current_app, jsonify, request

from sbll_cms.settings import ApiKeys, Settings
from sbll_cms.views.blueprints import settings_bp


@settings_bp.route("/api", methods=["POST"])
def settings_api_update():
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

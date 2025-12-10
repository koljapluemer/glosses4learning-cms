from __future__ import annotations

from flask import current_app, jsonify

from sbll_cms.views.blueprints import settings_bp


@settings_bp.route("/api", methods=["GET"])
def settings_api_get():
    store = current_app.extensions["settings_store"]
    current = store.load()
    return jsonify(current.to_dict())

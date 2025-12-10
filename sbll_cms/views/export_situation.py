from __future__ import annotations

from flask import abort, send_file, request

from sbll_cms.situations_logic import create_situation_export_zip
from sbll_cms.storage import get_storage
from sbll_cms.views.blueprints import situations_bp


@situations_bp.route("/glosses/<language>/<slug>/export-situation", methods=["GET"])
def export_situation(language: str, slug: str):
    storage = get_storage()
    situation = storage.load_gloss(language, slug)
    if not situation:
        abort(404)
    target_language = (request.values.get("target_language") or "").strip().lower()
    native_language = (request.values.get("native_language") or "").strip().lower()
    if not target_language or not native_language:
        abort(400, description="native_language and target_language are required")

    zip_buffer, _stats = create_situation_export_zip(situation, storage, native_language, target_language)

    if zip_buffer is None:
        abort(400, description="No learnable content for this language pair")

    filename = f"{language}-{slug}-{native_language}-{target_language}-export.zip"
    return send_file(zip_buffer, mimetype="application/zip", as_attachment=True, download_name=filename)

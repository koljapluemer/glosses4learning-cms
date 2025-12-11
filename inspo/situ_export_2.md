```py
from __future__ import annotations

from flask import current_app, render_template, request

from sbll_cms.situations_logic import perform_batch_export
from sbll_cms.storage import get_storage
from sbll_cms.entities.language import get_language_store
from sbll_cms.views.blueprints import situations_bp


@situations_bp.route("/batch-export-situations", methods=["GET", "POST"])
def batch_export_situations():
    storage = get_storage()
    language_store = get_language_store()

    if request.method == "GET":
        situations = []
        for g in storage.list_glosses():
            tags = g.tags or []
            if any(t == "eng:situation" for t in tags):
                situations.append(g)

        languages = language_store.list_languages()

        pairs_per_situation = len(languages) * (len(languages) - 1) if len(languages) >= 2 else 0
        max_exports = len(situations) * pairs_per_situation

        return render_template(
            "routes/batch_export_situations.html",
            situations=situations,
            languages=languages,
            pairs_per_situation=pairs_per_situation,
            max_exports=max_exports,
        )

    project_root = current_app.config["DATA_ROOT"].parent
    output_root = project_root / "situations"

    try:
        result = perform_batch_export(storage, language_store, output_root)
    except Exception as e:  # noqa: BLE001
        result = {
            "success": False,
            "error": str(e),
            "total_situations": 0,
            "total_exports": 0,
            "exports": [],
            "skipped": [],
        }

    return render_template(
        "routes/batch_export_situations_result.html",
        result=result,
        output_root=str(output_root),
    )
```
from __future__ import annotations

from flask import render_template

from sbll_cms.storage import get_storage
from sbll_cms.views.blueprints import situations_bp


@situations_bp.route("/situations", methods=["GET"])
def list_situations():
    storage = get_storage()
    glosses = []
    for g in storage.list_glosses():
        tags = g.tags or []
        if any(t == "eng:situation" for t in tags):
            glosses.append(g)
    return render_template("routes/list_situations.html", glosses=glosses)

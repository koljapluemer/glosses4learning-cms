from __future__ import annotations

from collections import defaultdict

from flask import render_template

from sbll_cms.entities.gloss import Gloss
from sbll_cms.storage import get_storage
from sbll_cms.utils.normalize_language_code import normalize_language_code
from sbll_cms.views.blueprints import glosses_bp


@glosses_bp.route("/", endpoint="index")
def index():
    storage = get_storage()
    glosses = storage.list_glosses()
    grouped: dict[str, list[Gloss]] = defaultdict(list)
    for gloss in glosses:
        grouped[normalize_language_code(gloss.language)].append(gloss)
    sorted_languages = sorted(grouped.items(), key=lambda item: item[0])
    return render_template("index.html", grouped_glosses=sorted_languages)

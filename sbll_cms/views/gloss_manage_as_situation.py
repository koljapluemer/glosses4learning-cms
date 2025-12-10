from __future__ import annotations

import json

from flask import abort, render_template, request

from sbll_cms.situations_logic import build_goal_nodes, render_tree
from sbll_cms.storage import get_storage
from sbll_cms.entities.language import get_language_store
from sbll_cms.views.blueprints import situations_bp


@situations_bp.route("/glosses/<language>/<slug>/manage-situation", methods=["GET"])
def gloss_manage_as_situation(language: str, slug: str):
    storage = get_storage()
    situation = storage.load_gloss(language, slug)
    if not situation:
        abort(404)
    target_language = (request.values.get("target_language") or "").strip().lower()
    native_language = (request.values.get("native_language") or "").strip().lower()

    languages = get_language_store().list_languages()
    tree_lines: list[str] = []
    affected_refs: list[str] = []
    missing_translation_refs: list[str] = []
    missing_target_refs: list[str] = []
    missing_usage_refs: list[str] = []
    stats = {}

    goal_nodes = []
    glosses_to_learn = []
    if native_language and target_language:
        goal_nodes, stats = build_goal_nodes(
            situation,
            storage=storage,
            native_language=native_language,
            target_language=target_language,
        )
        tree_lines = render_tree(goal_nodes)
        affected_refs = list(stats.get("parts_missing", set()))
        missing_translation_refs = list(stats.get("native_missing", set()))
        missing_target_refs = list(stats.get("target_missing", set()))
        missing_usage_refs = list(stats.get("usage_missing", set()))
        glosses_to_learn = list(stats.get("glosses_to_learn", set()))

    return render_template(
        "routes/gloss_manage_as_situation.html",
        situation=situation,
        tree_lines=tree_lines,
        target_language=target_language,
        native_language=native_language,
        languages=languages,
        break_up_refs_json=json.dumps(affected_refs),
        break_up_count=len(affected_refs),
        missing_translation_refs_json=json.dumps(missing_translation_refs),
        missing_translation_count=len(missing_translation_refs),
        missing_target_refs_json=json.dumps(missing_target_refs),
        missing_target_count=len(missing_target_refs),
        missing_usage_refs_json=json.dumps(missing_usage_refs),
        missing_usage_count=len(missing_usage_refs),
        goal_nodes=goal_nodes,
        glosses_to_learn=glosses_to_learn,
    )

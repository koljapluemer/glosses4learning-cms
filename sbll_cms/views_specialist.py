from __future__ import annotations

from datetime import datetime
import json
import re
import io
import zipfile

import requests
from markupsafe import Markup
from flask import Blueprint, abort, render_template, request, current_app, send_file

from .storage import get_storage
from .language import get_language_store
from .utils import paraphrase_display
from .relations import attach_relation
from .translation_tool import TranslationRequest, translate

bp = Blueprint("specialist", __name__)

SPLIT_LOG_MARKER = "SPLIT_CONSIDERED_UNNECESSARY"
TRANSLATION_IMPOSSIBLE_MARKER = "TRANSLATION_CONSIDERED_IMPOSSIBLE"
USAGE_IMPOSSIBLE_MARKER = "USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE"
REF_PATTERN = re.compile(r"^[a-z]{3}:[^:]+$")


@bp.route("/")
def specialist_index():
    links = [
        {"name": "Situation Management", "description": "Manage situation-tagged glosses.", "url": "/specialist/situations"},
    ]
    return render_template("specialist/index.html", links=links)


@bp.route("/situations")
def situation_list():
    storage = get_storage()
    glosses = []
    for g in storage.list_glosses():
        tags = g.tags or []
        if any(t == "eng:situation" for t in tags):
            glosses.append(g)
    return render_template("specialist/situations_list.html", glosses=glosses)


@bp.route("/situations/<language>/<slug>", methods=["GET"])
def manage_situation(language: str, slug: str):
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

    return render_template(
        "specialist/situation_manage.html",
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
        goal_nodes=goal_nodes if native_language and target_language else [],
        glosses_to_learn=list(stats.get("glosses_to_learn", set())) if native_language and target_language else [],
    )


def create_situation_export_zip(situation, storage, native_language: str, target_language: str):
    """
    Create a ZIP export for a single situation/language pair.

    Returns:
        tuple: (zip_buffer, stats) where zip_buffer is None if no learnable content exists
    """
    goal_nodes, stats = build_goal_nodes(
        situation,
        storage=storage,
        native_language=native_language,
        target_language=target_language,
    )

    # Return None if no goals (skip condition)
    if not goal_nodes:
        return None, stats

    def node_ref(node):
        gl = node["gloss"]
        return f"{gl.language}:{gl.slug or gl.content}"

    def gather_refs(root_node):
        refs = []
        learn_refs = []
        seen = set()

        def walk(n):
            ref = node_ref(n)
            if ref not in seen:
                seen.add(ref)
                refs.append(ref)
            if n.get("bold") and ref != node_ref(root_node):
                if ref not in learn_refs:
                    learn_refs.append(ref)
            for child in n.get("children", []):
                walk(child)

        walk(root_node)
        return refs, learn_refs

    export_obj = {
        "procedural-paraphrase-expression-goals": [],
        "understand-expression-goals": [],
    }
    all_refs: set[str] = set()

    # include situation gloss and translations into selected languages
    all_refs.add(f"{situation.language}:{situation.slug}")
    for ref in situation.translations or []:
        if ref.startswith(f"{native_language}:") or ref.startswith(f"{target_language}:"):
            all_refs.add(ref)

    for root in goal_nodes:
        goal_type = root.get("goal_type")
        if goal_type not in ("procedural", "understand"):
            continue
        refs, learn_refs = gather_refs(root)
        all_refs.update(refs)
        payload = {
            "finalChallenge": node_ref(root),
            "needToBeLearned": learn_refs,
            "references": refs,
        }
        if goal_type == "procedural":
            export_obj["procedural-paraphrase-expression-goals"].append(payload)
        else:
            export_obj["understand-expression-goals"].append(payload)

    jsonl_lines = []
    for ref in all_refs:
        gloss = storage.resolve_reference(ref)
        if not gloss:
            continue
        item = gloss.to_dict()
        item["ref"] = ref
        jsonl_lines.append(json.dumps(item, ensure_ascii=False))

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("situation.json", json.dumps(export_obj, ensure_ascii=False, indent=2))
        zf.writestr("glosses.jsonl", "\n".join(jsonl_lines))
    buf.seek(0)

    # Calculate stats for reporting
    stats["goal_count"] = len(goal_nodes)
    stats["gloss_count"] = len(all_refs)

    return buf, stats


@bp.route("/situations/<language>/<slug>/export", methods=["GET"])
def export_situation(language: str, slug: str):
    storage = get_storage()
    situation = storage.load_gloss(language, slug)
    if not situation:
        abort(404)
    target_language = (request.values.get("target_language") or "").strip().lower()
    native_language = (request.values.get("native_language") or "").strip().lower()
    if not target_language or not native_language:
        abort(400, description="native_language and target_language are required")

    zip_buffer, stats = create_situation_export_zip(situation, storage, native_language, target_language)

    if zip_buffer is None:
        abort(400, description="No learnable content for this language pair")

    filename = f"{language}-{slug}-{native_language}-{target_language}-export.zip"
    return send_file(zip_buffer, mimetype="application/zip", as_attachment=True, download_name=filename)


def perform_batch_export(storage, language_store, output_root):
    """
    Export all situations for all language pairs to disk.

    Returns dict with: success, total_situations, total_exports, exports[], skipped[], error
    Raises: Any exception (fail fast)
    """
    from pathlib import Path

    result = {
        "success": False,
        "total_situations": 0,
        "total_exports": 0,
        "exports": [],
        "skipped": [],
        "error": None,
    }

    try:
        # Find all situations (glosses tagged with "eng:situation")
        situations = []
        for g in storage.list_glosses():
            tags = g.tags or []
            if any(t == "eng:situation" for t in tags):
                situations.append(g)

        result["total_situations"] = len(situations)

        if not situations:
            result["success"] = True
            return result

        # Get all languages
        languages = language_store.list_languages()
        if len(languages) < 2:
            result["error"] = "Need at least 2 configured languages"
            return result

        # Process each situation × language pair
        for situation in situations:
            for native_lang in languages:
                for target_lang in languages:
                    if native_lang.iso_code == target_lang.iso_code:
                        continue

                    # Build goal nodes to get export data
                    goal_nodes, stats = build_goal_nodes(
                        situation, storage=storage,
                        native_language=native_lang.iso_code,
                        target_language=target_lang.iso_code
                    )

                    # Skip if no learnable content
                    if not goal_nodes:
                        result["skipped"].append({
                            "situation": f"{situation.language}:{situation.slug}",
                            "native": native_lang.iso_code,
                            "target": target_lang.iso_code,
                            "reason": "No learnable content",
                        })
                        continue

                    # Helper functions for building export data
                    def node_ref(node):
                        gl = node["gloss"]
                        return f"{gl.language}:{gl.slug or gl.content}"

                    def gather_refs(root_node):
                        refs = []
                        learn_refs = []
                        seen = set()

                        def walk(n):
                            ref = node_ref(n)
                            if ref not in seen:
                                seen.add(ref)
                                refs.append(ref)
                            if n.get("bold") and ref != node_ref(root_node):
                                if ref not in learn_refs:
                                    learn_refs.append(ref)
                            for child in n.get("children", []):
                                walk(child)

                        walk(root_node)
                        return refs, learn_refs

                    # Build export object
                    export_obj = {
                        "procedural-paraphrase-expression-goals": [],
                        "understand-expression-goals": [],
                    }
                    all_refs: set[str] = set()

                    # Include situation gloss and translations
                    all_refs.add(f"{situation.language}:{situation.slug}")
                    for ref in situation.translations or []:
                        if ref.startswith(f"{native_lang.iso_code}:") or ref.startswith(f"{target_lang.iso_code}:"):
                            all_refs.add(ref)

                    for root in goal_nodes:
                        goal_type = root.get("goal_type")
                        if goal_type not in ("procedural", "understand"):
                            continue
                        refs, learn_refs = gather_refs(root)
                        all_refs.update(refs)
                        payload = {
                            "finalChallenge": node_ref(root),
                            "needToBeLearned": learn_refs,
                            "references": refs,
                        }
                        if goal_type == "procedural":
                            export_obj["procedural-paraphrase-expression-goals"].append(payload)
                        else:
                            export_obj["understand-expression-goals"].append(payload)

                    # Collect glosses
                    jsonl_lines = []
                    for ref in all_refs:
                        gloss = storage.resolve_reference(ref)
                        if not gloss:
                            continue
                        item = gloss.to_dict()
                        item["ref"] = ref
                        jsonl_lines.append(json.dumps(item, ensure_ascii=False))

                    # Build output directory: situations/{native}/{target}/
                    output_dir = Path(output_root) / native_lang.iso_code / target_lang.iso_code
                    output_dir.mkdir(parents=True, exist_ok=True)

                    # Use situation content for filename
                    base_filename = situation.content

                    # Write situation.json
                    situation_json_path = output_dir / f"{base_filename}.json"
                    with situation_json_path.open("w", encoding="utf-8") as f:
                        json.dump(export_obj, f, ensure_ascii=False, indent=2)

                    # Write glosses.jsonl
                    glosses_jsonl_path = output_dir / f"{base_filename}.jsonl"
                    with glosses_jsonl_path.open("w", encoding="utf-8") as f:
                        f.write("\n".join(jsonl_lines))

                    result["exports"].append({
                        "situation": f"{situation.language}:{situation.slug}",
                        "native": native_lang.iso_code,
                        "target": target_lang.iso_code,
                        "situation_json": str(situation_json_path),
                        "glosses_jsonl": str(glosses_jsonl_path),
                        "stats": {
                            "goal_count": len(goal_nodes),
                            "gloss_count": len(all_refs),
                        },
                    })
                    result["total_exports"] += 1

        result["success"] = True
        return result

    except Exception as e:
        result["error"] = str(e)
        result["success"] = False
        raise  # Fail fast


def build_goal_nodes(situation, storage, native_language: str, target_language: str):
    stats = {
        "situation_glosses": set(),
        "glosses_to_learn": set(),
        "native_missing": set(),
        "target_missing": set(),
        "parts_missing": set(),
        "usage_missing": set(),
        "gloss_map": {},
    }
    seen_keys: set[str] = set()
    nodes = []

    def gloss_key(gl):
        return f"{gl.language}:{gl.slug or gl.content}"

    def has_log(gl, marker: str) -> bool:
        logs = getattr(gl, "logs", {}) or {}
        if not isinstance(logs, dict):
            return False
        return any(marker in str(val) for val in logs.values())

    def has_translation(gl, lang: str) -> bool:
        return any(ref.startswith(f"{lang}:") for ref in (gl.translations or []))

    def mark_stats(gl, usage_lineage: bool, parts_line: bool, learn_lang: str):
        key = gloss_key(gl)
        stats["gloss_map"][key] = gl
        stats["situation_glosses"].add(key)

        if not (getattr(gl, "parts", None) or []) and not has_log(gl, SPLIT_LOG_MARKER):
            stats["parts_missing"].add(key)

        if gl.language == target_language:
            if not has_translation(gl, native_language) and not has_log(gl, f"{TRANSLATION_IMPOSSIBLE_MARKER}:{native_language}"):
                stats["native_missing"].add(key)
            if not usage_lineage and not has_log(gl, f"{USAGE_IMPOSSIBLE_MARKER}:{target_language}") and not (gl.usage_examples or []):
                stats["usage_missing"].add(key)
        elif gl.language == native_language:
            if not has_translation(gl, target_language) and not has_log(gl, f"{TRANSLATION_IMPOSSIBLE_MARKER}:{target_language}"):
                stats["target_missing"].add(key)

        if parts_line and gl.language == learn_lang:
            stats["glosses_to_learn"].add(key)

        return {
            "warn_native_missing": key in stats["native_missing"],
            "warn_target_missing": key in stats["target_missing"],
            "warn_usage_missing": key in stats["usage_missing"],
        }

    def build_node(gloss, role="root", marker="", usage_lineage=False, allow_translations=True, path=None, parts_line=False, learn_lang=""):
        tags = gloss.tags or []
        if gloss.language == target_language and "eng:paraphrase" in tags:
            return None

        path = set(path or [])
        key = gloss_key(gloss)
        already_seen = key in seen_keys
        seen_keys.add(key)

        flags = mark_stats(gloss, usage_lineage, parts_line, learn_lang)

        node = {
            "gloss": gloss,
            "children": [],
            "marker": marker,
            "bold": parts_line and gloss.language == learn_lang,
            "role": role,
            "warn_native_missing": flags["warn_native_missing"],
            "warn_target_missing": flags["warn_target_missing"],
            "warn_usage_missing": flags["warn_usage_missing"],
            "warn_parts_missing": key in stats["parts_missing"],
        }

        if key in path:
            return node
        next_path = set(path)
        next_path.add(key)

        if role in ("root", "part", "usage_part"):
            stats["glosses_to_learn"].add(key)

        # parts recursion
        for part_ref in getattr(gloss, "parts", []):
            part_gloss = storage.resolve_reference(part_ref)
            if not part_gloss:
                continue
            part_node = build_node(
                part_gloss,
                role="usage_part" if role in ("usage", "usage_part") else "part",
                usage_lineage=usage_lineage,
                allow_translations=True,
                path=next_path,
                parts_line=True,
                learn_lang=learn_lang,
            )
            if part_node:
                node["children"].append(part_node)

        # translations
        if allow_translations:
            other_lang = None
            if gloss.language == native_language and target_language:
                other_lang = target_language
            elif gloss.language == target_language and native_language:
                other_lang = native_language
            if other_lang:
                for ref in gloss.translations or []:
                    ref_lang = ref.split(":", 1)[0].strip().lower()
                    if ref_lang != other_lang.lower():
                        continue
                    t_gloss = storage.resolve_reference(ref)
                    if not t_gloss:
                        continue
                    child_key = gloss_key(t_gloss)
                    t_node = build_node(
                        t_gloss,
                        role="translation",
                        marker="",
                        usage_lineage=usage_lineage,
                        allow_translations=child_key not in seen_keys,
                        path=next_path,
                        parts_line=False,
                        learn_lang=learn_lang,
                    )
                    if t_node:
                        node["children"].append(t_node)

        # usage examples
        if gloss.language == target_language and not usage_lineage:
            if gloss.usage_examples:
                for u_ref in getattr(gloss, "usage_examples", []):
                    u_gloss = storage.resolve_reference(u_ref)
                    if not u_gloss:
                        continue
                    child_key = gloss_key(u_gloss)
                    usage_node = build_node(
                        u_gloss,
                        role="usage",
                        marker="🛠 ",
                        usage_lineage=True,
                        allow_translations=child_key not in seen_keys,
                        path=next_path,
                        parts_line=False,
                        learn_lang=learn_lang,
                    )
                    if usage_node:
                        node["children"].append(usage_node)

        return node

    for ref in situation.children:
        gloss = storage.resolve_reference(ref)
        if not gloss:
            continue
        tags = gloss.tags or []
        marker = ""
        if gloss.language == native_language and "eng:procedural-paraphrase-expression-goal" in tags:
            marker = "⚙︎ "
            learn_lang = native_language
            goal_type = "procedural"
        elif gloss.language == target_language and "eng:understand-expression-goal" in tags:
            marker = "🗣 "
            learn_lang = target_language
            goal_type = "understand"
        else:
            continue
        node = build_node(
            gloss,
            role="root",
            marker=marker,
            usage_lineage=False,
            allow_translations=True,
            parts_line=True,
            learn_lang=learn_lang,
        )
        if node:
            node["goal_type"] = goal_type
            nodes.append(node)
    return nodes, stats


def render_tree(nodes):
    lines: list[str] = []

    def label_for(node):
        gloss = node["gloss"]
        text = paraphrase_display(gloss)
        slug = gloss.slug or ""
        url = f"/glosses/{gloss.language}/{slug}/edit"
        markers_after = ""
        if node.get("warn_native_missing") or node.get("warn_target_missing"):
            markers_after += " ⚠"
        if node.get("warn_usage_missing"):
            markers_after += " 🛠?"
        if node.get("warn_parts_missing"):
            markers_after += " ⫼?"
        content = f'<a class="link link-primary" target="_blank" href="{url}">{text}</a>{markers_after}'
        if node.get("bold"):
            content = f"<strong>{content}</strong>"
        return Markup(content)

    def walk(node_list, prefix=""):
        total = len(node_list)
        for idx, node in enumerate(node_list):
            is_last = idx == total - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{node.get('marker', '')}{label_for(node)}")
            if node.get("children"):
                walk(node["children"], f"{prefix}{'    ' if is_last else '│   '}")

    walk(nodes)
    return lines


@bp.route("/situations/tools/break-up", methods=["GET", "POST"])
def break_up_glosses():
    storage = get_storage()

    refs_raw = request.values.get("refs") or "[]"
    action = (request.form.get("action") or "").strip()
    target_ref = (request.form.get("ref") or "").strip()
    selected_refs = [r.strip() for r in (request.form.getlist("selected_ref") or []) if r.strip() and REF_PATTERN.match(r.strip())]
    selected_parts = [p for p in (request.form.getlist("selected_part") or []) if p.strip()]
    provider_model = request.form.get("provider_model") or "OpenAI|gpt-4o-mini"
    context = request.form.get("context") or ""
    results_raw = request.form.get("results_json") or "[]"
    ai_results = parse_ai_results(results_raw)
    ai_error = None
    ai_message = None
    settings = current_app.extensions["settings_store"].load()
    refs = parse_refs(refs_raw)

    if request.method == "POST":
        if action == "mark_skip":
            targets = selected_refs or ([target_ref] if target_ref and REF_PATTERN.match(target_ref) else [])
            for ref in targets:
                if not REF_PATTERN.match(ref):
                    continue
                gloss = storage.resolve_reference(ref)
                if gloss:
                    logs = gloss.logs if isinstance(getattr(gloss, "logs", {}), dict) else {}
                    logs[datetime.utcnow().isoformat() + "Z"] = SPLIT_LOG_MARKER
                    gloss.logs = logs
                    storage.save_gloss(gloss)
        elif action == "ai_generate":
            provider, model = provider_model.split("|", 1) if "|" in provider_model else (provider_model, "")
            if not selected_refs:
                ai_error = "Select glosses to split."
            elif provider != "OpenAI":
                ai_error = "Only OpenAI is supported for now."
            elif not settings.api_keys.openai:
                ai_error = "OpenAI API key missing. Add it in Settings."
            else:
                ai_results = []
                for ref in selected_refs:
                    gloss = storage.resolve_reference(ref)
                    if not gloss:
                        continue
                    if not should_break_up(gloss):
                        continue
                    result = generate_split(gloss, model, settings.api_keys.openai, context)
                    ai_results.append({
                        "ref": f"{gloss.language}:{gloss.slug}",
                        "content": gloss.content,
                        "language": gloss.language,
                        "parts": result.get("parts") or [],
                        "error": result.get("error"),
                    })
                if not ai_results:
                    ai_error = "No eligible glosses found to split."
        elif action in ("ai_accept_all", "ai_accept_selection"):
            if not ai_results:
                ai_error = "No AI results to accept."
            else:
                added = 0
                selection_map: dict[str, list[str]] = {}
                if action == "ai_accept_selection":
                    for val in selected_parts:
                        try:
                            entry = json.loads(val)
                        except Exception:
                            continue
                        if not isinstance(entry, dict):
                            continue
                        ref = entry.get("ref")
                        part = entry.get("part")
                        if not ref or not isinstance(part, str):
                            continue
                        selection_map.setdefault(ref, []).append(part)
                for item in ai_results:
                    ref = item.get("ref", "")
                    if not REF_PATTERN.match(ref or ""):
                        continue
                    gloss = storage.resolve_reference(ref)
                    if not gloss:
                        continue
                    parts = item.get("parts") or []
                    chosen = parts if action == "ai_accept_all" else selection_map.get(ref, [])
                    for part_text in chosen:
                        part_text = part_text.strip()
                        if not part_text:
                            continue
                        part_gloss = storage.ensure_gloss(gloss.language, part_text)
                        attach_relation(storage, gloss, "parts", part_gloss)
                        added += 1
                ai_results = []
                ai_message = f"Added {added} parts." if added else "No parts added."
        elif action == "ai_discard":
            ai_results = []

    glosses: list = []
    seen: set[str] = set()
    for ref in refs:
        if ref in seen:
            continue
        seen.add(ref)
        gloss = storage.resolve_reference(ref)
        if gloss and should_break_up(gloss):
            glosses.append(gloss)

    return render_template(
        "specialist/break_up_glosses.html",
        glosses=glosses,
        refs_json=json.dumps(refs),
        provider_model=provider_model,
        context=context,
        ai_results=ai_results,
        ai_results_json=json.dumps(ai_results),
        ai_error=ai_error,
        ai_message=ai_message,
    )


@bp.route("/situations/tools/missing-translations", methods=["GET", "POST"])
def missing_translations_tool():
    storage = get_storage()
    refs_raw = request.values.get("refs") or "[]"
    native_language = (request.values.get("native_language") or "").strip().lower()
    target_language = (request.values.get("target_language") or "").strip().lower()
    action = (request.form.get("action") or "").strip()
    selected_refs = [r.strip() for r in (request.form.getlist("selected_ref") or []) if r.strip() and REF_PATTERN.match(r.strip())]
    selected_translations = [t for t in (request.form.getlist("selected_translation") or []) if t.strip()]
    provider_model = request.form.get("provider_model") or "OpenAI|gpt-4o-mini"
    context = request.form.get("context") or ""
    results_raw = request.form.get("results_json") or "[]"
    ai_results = parse_translation_results(results_raw)
    ai_error = None
    ai_message = None
    settings = current_app.extensions["settings_store"].load()
    refs = parse_refs(refs_raw)

    glosses: list = []
    seen: set[str] = set()
    if native_language and target_language:
        for ref in refs:
            if ref in seen:
                continue
            seen.add(ref)
            gloss = storage.resolve_reference(ref)
            if gloss and should_translate_missing(gloss, native_language, target_language):
                glosses.append(gloss)

    if request.method == "POST":
        if not native_language or not target_language:
            ai_error = "Both native_language and target_language are required."
        elif action == "mark_impossible":
            for ref in selected_refs:
                gloss = storage.resolve_reference(ref)
                if gloss:
                    logs = gloss.logs if isinstance(getattr(gloss, "logs", {}), dict) else {}
                    logs[datetime.utcnow().isoformat() + "Z"] = f"{TRANSLATION_IMPOSSIBLE_MARKER}:{native_language}"
                    gloss.logs = logs
                    storage.save_gloss(gloss)
            # refresh list
            glosses = [g for g in glosses if should_translate_missing(g, native_language, target_language)]
        elif action == "ai_generate":
            provider, model = provider_model.split("|", 1) if "|" in provider_model else (provider_model, "")
            if not selected_refs:
                ai_error = "Select glosses to translate."
            elif provider != "OpenAI":
                ai_error = "Only OpenAI is supported for now."
            elif not settings.api_keys.openai:
                ai_error = "OpenAI API key missing. Add it in Settings."
            else:
                ai_results = []
                for ref in selected_refs:
                    gloss = storage.resolve_reference(ref)
                    if not gloss or not should_translate_missing(gloss, native_language, target_language):
                        continue
                    req = TranslationRequest(
                        gloss=gloss,
                        target_language=native_language,
                        provider=provider,
                        model=model,
                        context=context,
                    )
                    result = translate(req, settings, get_language_store())
                    ai_results.append({
                        "ref": f"{gloss.language}:{gloss.slug}",
                        "content": gloss.content,
                        "language": gloss.language,
                        "translations": result.translations or [],
                        "error": result.error,
                    })
                if not ai_results:
                    ai_error = "No eligible glosses found to translate."
        elif action in ("ai_accept_all", "ai_accept_selection"):
            if not ai_results:
                ai_error = "No AI results to accept."
            else:
                added = 0
                selection_map: dict[str, list[str]] = {}
                if action == "ai_accept_selection":
                    for val in selected_translations:
                        try:
                            entry = json.loads(val)
                        except Exception:
                            continue
                        if not isinstance(entry, dict):
                            continue
                        ref = entry.get("ref")
                        translation = entry.get("translation")
                        if not ref or not isinstance(translation, str):
                            continue
                        selection_map.setdefault(ref, []).append(translation)
                for item in ai_results:
                    ref = item.get("ref", "")
                    if not REF_PATTERN.match(ref or ""):
                        continue
                    gloss = storage.resolve_reference(ref)
                    if not gloss:
                        continue
                    translations = item.get("translations") or []
                    chosen = translations if action == "ai_accept_all" else selection_map.get(ref, [])
                    for t_text in chosen:
                        t_text = t_text.strip()
                        if not t_text:
                            continue
                        target = storage.ensure_gloss(native_language, t_text)
                        attach_relation(storage, gloss, "translations", target)
                        added += 1
                ai_results = []
                ai_message = f"Added {added} translations." if added else "No translations added."
        elif action == "ai_discard":
            ai_results = []

    return render_template(
        "specialist/missing_translations.html",
        glosses=glosses,
        refs_json=json.dumps(refs),
        provider_model=provider_model,
        context=context,
        ai_results=ai_results,
        ai_results_json=json.dumps(ai_results),
        ai_error=ai_error,
        ai_message=ai_message,
        native_language=native_language,
        target_language=target_language,
    )


@bp.route("/situations/tools/missing-target-translations", methods=["GET", "POST"])
def missing_target_translations_tool():
    storage = get_storage()
    refs_raw = request.values.get("refs") or "[]"
    native_language = (request.values.get("native_language") or "").strip().lower()
    target_language = (request.values.get("target_language") or "").strip().lower()
    action = (request.form.get("action") or "").strip()
    selected_refs = [r.strip() for r in (request.form.getlist("selected_ref") or []) if r.strip() and REF_PATTERN.match(r.strip())]
    selected_translations = [t for t in (request.form.getlist("selected_translation") or []) if t.strip()]
    provider_model = request.form.get("provider_model") or "OpenAI|gpt-4o-mini"
    context = request.form.get("context") or ""
    results_raw = request.form.get("results_json") or "[]"
    ai_results = parse_translation_results(results_raw)
    ai_error = None
    ai_message = None
    settings = current_app.extensions["settings_store"].load()
    refs = parse_refs(refs_raw)

    glosses: list = []
    seen: set[str] = set()
    if native_language and target_language:
        for ref in refs:
            if ref in seen:
                continue
            seen.add(ref)
            gloss = storage.resolve_reference(ref)
            if gloss and should_translate_missing_into_target(gloss, native_language, target_language):
                glosses.append(gloss)

    if request.method == "POST":
        if not native_language or not target_language:
            ai_error = "Both native_language and target_language are required."
        elif action == "mark_impossible":
            for ref in selected_refs:
                gloss = storage.resolve_reference(ref)
                if gloss:
                    logs = gloss.logs if isinstance(getattr(gloss, "logs", {}), dict) else {}
                    logs[datetime.utcnow().isoformat() + "Z"] = f"{TRANSLATION_IMPOSSIBLE_MARKER}:{target_language}"
                    gloss.logs = logs
                    storage.save_gloss(gloss)
            glosses = [g for g in glosses if should_translate_missing_into_target(g, native_language, target_language)]
        elif action == "ai_generate":
            provider, model = provider_model.split("|", 1) if "|" in provider_model else (provider_model, "")
            if not selected_refs:
                ai_error = "Select glosses to translate."
            elif provider != "OpenAI":
                ai_error = "Only OpenAI is supported for now."
            elif not settings.api_keys.openai:
                ai_error = "OpenAI API key missing. Add it in Settings."
            else:
                ai_results = []
                for ref in selected_refs:
                    gloss = storage.resolve_reference(ref)
                    if not gloss or not should_translate_missing_into_target(gloss, native_language, target_language):
                        continue
                    req = TranslationRequest(
                        gloss=gloss,
                        target_language=target_language,
                        provider=provider,
                        model=model,
                        context=context,
                    )
                    result = translate(req, settings, get_language_store())
                    ai_results.append({
                        "ref": f"{gloss.language}:{gloss.slug}",
                        "content": gloss.content,
                        "language": gloss.language,
                        "translations": result.translations or [],
                        "error": result.error,
                    })
                if not ai_results:
                    ai_error = "No eligible glosses found to translate."
        elif action in ("ai_accept_all", "ai_accept_selection"):
            if not ai_results:
                ai_error = "No AI results to accept."
            else:
                added = 0
                selection_map: dict[str, list[str]] = {}
                if action == "ai_accept_selection":
                    for val in selected_translations:
                        try:
                            entry = json.loads(val)
                        except Exception:
                            continue
                        if not isinstance(entry, dict):
                            continue
                        ref = entry.get("ref")
                        translation = entry.get("translation")
                        if not ref or not isinstance(translation, str):
                            continue
                        selection_map.setdefault(ref, []).append(translation)
                for item in ai_results:
                    ref = item.get("ref", "")
                    if not REF_PATTERN.match(ref or ""):
                        continue
                    gloss = storage.resolve_reference(ref)
                    if not gloss:
                        continue
                    translations = item.get("translations") or []
                    chosen = translations if action == "ai_accept_all" else selection_map.get(ref, [])
                    for t_text in chosen:
                        t_text = t_text.strip()
                        if not t_text:
                            continue
                        target = storage.ensure_gloss(target_language, t_text)
                        attach_relation(storage, gloss, "translations", target)
                        added += 1
                ai_results = []
                ai_message = f"Added {added} translations." if added else "No translations added."
        elif action == "ai_discard":
            ai_results = []

    return render_template(
        "specialist/missing_target_translations.html",
        glosses=glosses,
        refs_json=json.dumps(refs),
        provider_model=provider_model,
        context=context,
        ai_results=ai_results,
        ai_results_json=json.dumps(ai_results),
        ai_error=ai_error,
        ai_message=ai_message,
        native_language=native_language,
        target_language=target_language,
    )


@bp.route("/situations/tools/missing-usage-examples", methods=["GET", "POST"])
def missing_usage_examples_tool():
    storage = get_storage()
    refs_raw = request.values.get("refs") or "[]"
    target_language = (request.values.get("target_language") or "").strip().lower()
    action = (request.form.get("action") or "").strip()
    selected_refs = [r.strip() for r in (request.form.getlist("selected_ref") or []) if r.strip() and REF_PATTERN.match(r.strip())]
    selected_examples = [t for t in (request.form.getlist("selected_example") or []) if t.strip()]
    provider_model = request.form.get("provider_model") or "OpenAI|gpt-4o-mini"
    context = request.form.get("context") or ""
    results_raw = request.form.get("results_json") or "[]"
    ai_results = parse_usage_results(results_raw)
    ai_error = None
    ai_message = None
    settings = current_app.extensions["settings_store"].load()
    refs = parse_refs(refs_raw)

    glosses: list = []
    seen: set[str] = set()
    if target_language:
        for ref in refs:
            if ref in seen:
                continue
            seen.add(ref)
            gloss = storage.resolve_reference(ref)
            if gloss and should_add_usage_examples(gloss, target_language):
                glosses.append(gloss)

    if request.method == "POST":
        if not target_language:
            ai_error = "target_language is required."
        elif action == "mark_impossible":
            for ref in selected_refs:
                gloss = storage.resolve_reference(ref)
                if gloss:
                    logs = gloss.logs if isinstance(getattr(gloss, "logs", {}), dict) else {}
                    logs[datetime.utcnow().isoformat() + "Z"] = f"{USAGE_IMPOSSIBLE_MARKER}:{target_language}"
                    gloss.logs = logs
                    storage.save_gloss(gloss)
            glosses = [g for g in glosses if should_add_usage_examples(g, target_language)]
        elif action == "ai_generate":
            provider, model = provider_model.split("|", 1) if "|" in provider_model else (provider_model, "")
            if not selected_refs:
                ai_error = "Select glosses to generate examples for."
            elif provider != "OpenAI":
                ai_error = "Only OpenAI is supported for now."
            elif not settings.api_keys.openai:
                ai_error = "OpenAI API key missing. Add it in Settings."
            else:
                ai_results = []
                for ref in selected_refs:
                    gloss = storage.resolve_reference(ref)
                    if not gloss or not should_add_usage_examples(gloss, target_language):
                        continue
                    result = generate_usage_examples(gloss, model, settings.api_keys.openai, context, get_language_store())
                    ai_results.append({
                        "ref": f"{gloss.language}:{gloss.slug}",
                        "content": gloss.content,
                        "language": gloss.language,
                        "examples": result.get("examples") or [],
                        "error": result.get("error"),
                    })
                if not ai_results:
                    ai_error = "No eligible glosses found to generate examples."
        elif action in ("ai_accept_all", "ai_accept_selection"):
            if not ai_results:
                ai_error = "No AI results to accept."
            else:
                added = 0
                selection_map: dict[str, list[str]] = {}
                if action == "ai_accept_selection":
                    for val in selected_examples:
                        try:
                            entry = json.loads(val)
                        except Exception:
                            continue
                        if not isinstance(entry, dict):
                            continue
                        ref = entry.get("ref")
                        example = entry.get("example")
                        if not ref or not isinstance(example, str):
                            continue
                        selection_map.setdefault(ref, []).append(example)
                for item in ai_results:
                    ref = item.get("ref", "")
                    if not REF_PATTERN.match(ref or ""):
                        continue
                    gloss = storage.resolve_reference(ref)
                    if not gloss:
                        continue
                    examples = item.get("examples") or []
                    chosen = examples if action == "ai_accept_all" else selection_map.get(ref, [])
                    for ex_text in chosen:
                        ex_text = ex_text.strip()
                        if not ex_text:
                            continue
                        ex_gloss = storage.ensure_gloss(gloss.language, ex_text)
                        attach_relation(storage, gloss, "usage_examples", ex_gloss)
                        added += 1
                ai_results = []
                ai_message = f"Added {added} usage examples." if added else "No usage examples added."
        elif action == "ai_discard":
            ai_results = []

    return render_template(
        "specialist/missing_usage_examples.html",
        glosses=glosses,
        refs_json=json.dumps(refs),
        provider_model=provider_model,
        context=context,
        ai_results=ai_results,
        ai_results_json=json.dumps(ai_results),
        ai_error=ai_error,
        ai_message=ai_message,
        target_language=target_language,
    )


@bp.route("/situations/batch-export", methods=["GET", "POST"])
def batch_export_situations():
    """Batch export all situations for all language pairs."""
    storage = get_storage()
    language_store = get_language_store()

    if request.method == "GET":
        # Preview page: show what will be exported
        situations = []
        for g in storage.list_glosses():
            tags = g.tags or []
            if any(t == "eng:situation" for t in tags):
                situations.append(g)

        languages = language_store.list_languages()

        pairs_per_situation = len(languages) * (len(languages) - 1) if len(languages) >= 2 else 0
        max_exports = len(situations) * pairs_per_situation

        return render_template(
            "specialist/batch_export.html",
            situations=situations,
            languages=languages,
            pairs_per_situation=pairs_per_situation,
            max_exports=max_exports,
        )

    # POST: Execute batch export
    project_root = current_app.config["DATA_ROOT"].parent
    output_root = project_root / "situations"

    try:
        result = perform_batch_export(storage, language_store, output_root)
    except Exception as e:
        result = {
            "success": False,
            "error": str(e),
            "total_situations": 0,
            "total_exports": 0,
            "exports": [],
            "skipped": [],
        }

    return render_template(
        "specialist/batch_export_result.html",
        result=result,
        output_root=str(output_root),
    )


def should_break_up(gloss) -> bool:
    no_parts = not (getattr(gloss, "parts", None) or [])
    logs = getattr(gloss, "logs", {}) or {}
    skip_marked = False
    if isinstance(logs, dict):
        skip_marked = any(SPLIT_LOG_MARKER in str(val) for val in logs.values())
    return no_parts and not skip_marked


def should_translate_missing(gloss, native_language: str, target_language: str) -> bool:
    if gloss.language != target_language:
        return False
    tags = gloss.tags or []
    if "eng:paraphrase" in tags:
        return False
    translations = gloss.translations or []
    has_native = any(ref.startswith(f"{native_language}:") for ref in translations)
    if has_native:
        return False
    logs = getattr(gloss, "logs", {}) or {}
    if isinstance(logs, dict):
        blocked = any(f"{TRANSLATION_IMPOSSIBLE_MARKER}:{native_language}" in str(val) for val in logs.values())
        if blocked:
            return False
    return True


def should_translate_missing_into_target(gloss, native_language: str, target_language: str) -> bool:
    if gloss.language != native_language:
        return False
    translations = gloss.translations or []
    has_target = any(ref.startswith(f"{target_language}:") for ref in translations)
    if has_target:
        return False
    logs = getattr(gloss, "logs", {}) or {}
    if isinstance(logs, dict):
        blocked = any(f"{TRANSLATION_IMPOSSIBLE_MARKER}:{target_language}" in str(val) for val in logs.values())
        if blocked:
            return False
    return True


def should_add_usage_examples(gloss, target_language: str, roles: set[str] | None = None) -> bool:
    if gloss.language != target_language:
        return False
    if roles and roles.issubset({"usage_part"}):
        return False
    tags = gloss.tags or []
    if "eng:paraphrase" in tags:
        return False
    examples = getattr(gloss, "usage_examples", []) or []
    if examples:
        return False
    logs = getattr(gloss, "logs", {}) or {}
    if isinstance(logs, dict):
        blocked = any(f"{USAGE_IMPOSSIBLE_MARKER}:{target_language}" in str(val) for val in logs.values())
        if blocked:
            return False
    return True


def parse_refs(raw: str) -> list[str]:
    try:
        parsed = json.loads(raw)
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []
    refs: list[str] = []
    pattern = re.compile(r"^[a-z]{3}:[^:]+$")
    for item in parsed:
        if not isinstance(item, str):
            continue
        val = item.strip()
        if val and pattern.match(val):
            refs.append(val)
    return refs


def parse_ai_results(raw: str) -> list[dict]:
    try:
        parsed = json.loads(raw)
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []
    cleaned = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        cleaned.append({
            "ref": item.get("ref"),
            "content": item.get("content"),
            "language": item.get("language"),
            "parts": item.get("parts") or [],
            "error": item.get("error"),
        })
    return cleaned


def parse_translation_results(raw: str) -> list[dict]:
    try:
        parsed = json.loads(raw)
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []
    cleaned = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        cleaned.append({
            "ref": item.get("ref"),
            "content": item.get("content"),
            "language": item.get("language"),
            "translations": item.get("translations") or [],
            "error": item.get("error"),
        })
    return cleaned


def parse_usage_results(raw: str) -> list[dict]:
    try:
        parsed = json.loads(raw)
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []
    cleaned = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        cleaned.append({
            "ref": item.get("ref"),
            "content": item.get("content"),
            "language": item.get("language"),
            "examples": item.get("examples") or [],
            "error": item.get("error"),
        })
    return cleaned


def generate_split(gloss, model: str, api_key: str, context: str = "") -> dict:
    prompt = (
        f"Take this {gloss.language} expression or phrase and break it up into parts "
        "that can be learned on their own, such as sub-expressions or words. "
        "Return a JSON object with a 'parts' array of strings. Avoid repetition."
    )
    if context:
        prompt += f" Context: {context}"
    prompt += f" Expression: {gloss.content}"
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model or "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a concise linguistic decomposition assistant."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 200,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "parts_list",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "parts": {"type": "array", "items": {"type": "string"}}
                            },
                            "required": ["parts"],
                            "additionalProperties": False,
                        },
                        "strict": True,
                    },
                },
            },
            timeout=30,
        )
        data = response.json()
        if response.status_code != 200:
            return {"parts": [], "error": data.get("error", {}).get("message", "OpenAI error")}
        content = data["choices"][0]["message"]["content"].strip()
        try:
            parsed = json.loads(content)
            parts = parsed.get("parts", []) if isinstance(parsed, dict) else []
        except Exception:
            parts = []
        parts = [p.strip() for p in parts if isinstance(p, str) and p.strip()]
        return {"parts": parts, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"parts": [], "error": str(exc)}


def generate_usage_examples(gloss, model: str, api_key: str, context: str, language_store):
    ai_note = ""
    lang_obj = language_store.get(gloss.language)
    if lang_obj and getattr(lang_obj, "ai_note", None):
        ai_note = lang_obj.ai_note

    prompt = (
        f"Return three short, easily understandable, real, natural language examples that utilize the expression '{gloss.content}' "
        "in {language}. Each example should be a single sentence and practical for learners. "
        "Respond as JSON with an 'examples' array of strings."
    ).format(language=gloss.language)
    if ai_note:
        prompt += f" Notes for this language: {ai_note}."
    if context:
        prompt += f" Additional context: {context}"
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model or "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a concise language learning assistant returning structured examples."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 220,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "usage_examples",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "examples": {"type": "array", "items": {"type": "string"}}
                            },
                            "required": ["examples"],
                            "additionalProperties": False,
                        },
                        "strict": True,
                    },
                },
            },
            timeout=30,
        )
        data = response.json()
        if response.status_code != 200:
            return {"examples": [], "error": data.get("error", {}).get("message", "OpenAI error")}
        content = data["choices"][0]["message"]["content"].strip()
        try:
            parsed = json.loads(content)
            examples = parsed.get("examples", []) if isinstance(parsed, dict) else []
        except Exception:
            examples = []
        examples = [ex.strip() for ex in examples if isinstance(ex, str) and ex.strip()]
        return {"examples": examples, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"examples": [], "error": str(exc)}

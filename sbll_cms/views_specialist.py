from __future__ import annotations

from datetime import datetime
import json
import re

import requests
from markupsafe import Markup
from flask import Blueprint, abort, render_template, request, current_app

from .storage import get_storage
from .language import get_language_store
from .utils import paraphrase_display
from .relations import attach_relation
from .translation_tool import TranslationRequest, translate

bp = Blueprint("specialist", __name__)

SPLIT_LOG_MARKER = "SPLIT_CONSIDERED_UNNECESSARY"
TRANSLATION_IMPOSSIBLE_MARKER = "TRANSLATION_CONSIDERED_IMPOSSIBLE"
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

    if native_language and target_language:
        goal_nodes = build_goal_nodes(
            situation,
            storage=storage,
            native_language=native_language,
            target_language=target_language,
        )
        tree_lines = render_tree(goal_nodes)
        glosses_in_tree = collect_glosses(goal_nodes)
        affected_refs = [
            f"{g.language}:{g.slug}"
            for g in glosses_in_tree
            if g.slug and should_break_up(g)
        ]
        missing_translation_refs = [
            f"{g.language}:{g.slug}"
            for g in glosses_in_tree
            if g.slug and should_translate_missing(g, native_language, target_language)
        ]

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
    )


def build_goal_nodes(situation, storage, native_language: str, target_language: str):
    nodes = []
    for ref in situation.children:
        gloss = storage.resolve_reference(ref)
        if not gloss:
            continue
        tags = gloss.tags or []
        if gloss.language == target_language and "eng:paraphrase" in tags:
            continue
        marker = ""
        if gloss.language == native_language and "eng:procedural-paraphrase-expression-goal" in tags:
            marker = "⚙︎ "
        elif gloss.language == target_language and "eng:understand-expression-goal" in tags:
            marker = "🗣 "
        else:
            continue
        node = build_tree_node(
            gloss,
            storage=storage,
            native_language=native_language,
            target_language=target_language,
            role="root",
            marker=marker,
            path=set(),
        )
        if node:
            nodes.append(node)
    return nodes


def build_tree_node(
    gloss,
    storage,
    native_language: str,
    target_language: str,
    role: str = "root",
    marker: str = "",
    path: set[str] | None = None,
):
    path = path or set()
    key = f"{gloss.language}:{gloss.slug or gloss.content}"
    node = {"gloss": gloss, "children": [], "marker": marker, "bold": role in ("part", "usage_part"), "role": role}

    tags = gloss.tags or []
    if gloss.language == target_language and "eng:paraphrase" in tags:
        return None

    if key in path:
        return node

    next_path = set(path)
    next_path.add(key)

    if role in ("root", "part", "usage", "usage_part"):
        for part_ref in getattr(gloss, "parts", []):
            part_gloss = storage.resolve_reference(part_ref)
            if not part_gloss:
                continue
            part_role = "usage_part" if role in ("usage", "usage_part") else "part"
            part_node = build_tree_node(
                part_gloss,
                storage=storage,
                native_language=native_language,
                target_language=target_language,
                role=part_role,
                path=next_path,
            )
            if part_node:
                part_node["bold"] = True
                node["children"].append(part_node)

    if role in ("root", "part"):
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
                if t_gloss:
                    t_node = build_tree_node(
                        t_gloss,
                        storage=storage,
                        native_language=native_language,
                        target_language=target_language,
                        role="translation",
                        path=next_path,
                    )
                    if t_node:
                        node["children"].append(t_node)
    elif role == "usage_part" and native_language:
        for ref in gloss.translations or []:
            ref_lang = ref.split(":", 1)[0].strip().lower()
            if ref_lang != native_language.lower():
                continue
            t_gloss = storage.resolve_reference(ref)
            if t_gloss:
                t_node = build_tree_node(
                    t_gloss,
                    storage=storage,
                    native_language=native_language,
                    target_language=target_language,
                    role="translation",
                    path=next_path,
                )
                if t_node:
                    node["children"].append(t_node)

    if gloss.language == target_language:
        for u_ref in getattr(gloss, "usage_examples", []):
            u_gloss = storage.resolve_reference(u_ref)
            if not u_gloss:
                continue
            usage_node = build_tree_node(
                u_gloss,
                storage=storage,
                native_language=native_language,
                target_language=target_language,
                role="usage",
                marker="🛠 ",
                path=next_path,
            )
            if usage_node:
                node["children"].append(usage_node)

    return node


def render_tree(nodes):
    lines: list[str] = []

    def label_for(node):
        gloss = node["gloss"]
        text = paraphrase_display(gloss)
        slug = gloss.slug or ""
        url = f"/glosses/{gloss.language}/{slug}/edit"
        content = f'<a class="link link-primary" target="_blank" href="{url}">{text}</a>'
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


def collect_glosses(nodes):
    seen: set[str] = set()
    ordered = []

    def walk(node_list):
        for node in node_list:
            gloss = node["gloss"]
            ref = f"{gloss.language}:{gloss.slug or gloss.content}"
            if ref not in seen:
                seen.add(ref)
                ordered.append(gloss)
            for child in node.get("children", []):
                walk([child])

    walk(nodes)
    return ordered


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

from __future__ import annotations

from datetime import datetime
import json

from markupsafe import Markup
from flask import Blueprint, abort, render_template, request

from .storage import get_storage
from .language import get_language_store
from .utils import paraphrase_display

bp = Blueprint("specialist", __name__)

SPLIT_LOG_MARKER = "SPLIT_CONSIDERED_UNNECESSARY"


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

    return render_template(
        "specialist/situation_manage.html",
        situation=situation,
        tree_lines=tree_lines,
        target_language=target_language,
        native_language=native_language,
        languages=languages,
        break_up_refs_json=json.dumps(affected_refs),
        break_up_count=len(affected_refs),
    )


def build_goal_nodes(situation, storage, native_language: str, target_language: str):
    nodes = []
    for ref in situation.children:
        gloss = storage.resolve_reference(ref)
        if not gloss:
            continue
        tags = gloss.tags or []
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
                    node["children"].append(
                        build_tree_node(
                            t_gloss,
                            storage=storage,
                            native_language=native_language,
                            target_language=target_language,
                            role="translation",
                            path=next_path,
                        )
                    )
    elif role == "usage_part" and native_language:
        for ref in gloss.translations or []:
            ref_lang = ref.split(":", 1)[0].strip().lower()
            if ref_lang != native_language.lower():
                continue
            t_gloss = storage.resolve_reference(ref)
            if t_gloss:
                node["children"].append(
                    build_tree_node(
                        t_gloss,
                        storage=storage,
                        native_language=native_language,
                        target_language=target_language,
                        role="translation",
                        path=next_path,
                    )
                )

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


@bp.route("/situations/tools/break-up", methods=["POST"])
def break_up_glosses():
    storage = get_storage()
    refs_raw = request.form.get("refs") or "[]"
    action = (request.form.get("action") or "").strip()
    target_ref = (request.form.get("ref") or "").strip()
    refs = parse_refs(refs_raw)

    if action == "mark_skip" and target_ref:
        gloss = storage.resolve_reference(target_ref)
        if gloss:
            logs = gloss.logs if isinstance(getattr(gloss, "logs", {}), dict) else {}
            logs[datetime.utcnow().isoformat() + "Z"] = SPLIT_LOG_MARKER
            gloss.logs = logs
            storage.save_gloss(gloss)

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
    )


def should_break_up(gloss) -> bool:
    no_parts = not (getattr(gloss, "parts", None) or [])
    logs = getattr(gloss, "logs", {}) or {}
    skip_marked = False
    if isinstance(logs, dict):
        skip_marked = any(SPLIT_LOG_MARKER in str(val) for val in logs.values())
    return no_parts and not skip_marked


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
    for item in parsed:
        if not isinstance(item, str):
            continue
        val = item.strip()
        if val:
            refs.append(val)
    return refs

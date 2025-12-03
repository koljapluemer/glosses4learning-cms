from __future__ import annotations

from markupsafe import Markup
from flask import Blueprint, abort, render_template

from .storage import get_storage
from .utils import paraphrase_display

bp = Blueprint("specialist", __name__)


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


@bp.route("/situations/<language>/<slug>")
def manage_situation(language: str, slug: str):
    storage = get_storage()
    situation = storage.load_gloss(language, slug)
    if not situation:
        abort(404)

    def resolve(ref: str):
        return storage.resolve_reference(ref)

    root_nodes = []
    for ref in situation.children:
        gloss = resolve(ref)
        if not gloss or "eng:expression-goal" not in (gloss.tags or []):
            continue
        node = {"gloss": gloss, "children": build_part_nodes(gloss, resolve)}
        root_nodes.append(node)

    tree_lines = render_tree(root_nodes)
    return render_template("specialist/situation_manage.html", situation=situation, tree_lines=tree_lines)


def build_part_nodes(gloss, resolve_func):
    children = []
    for ref in gloss.parts:
        part = resolve_func(ref)
        if not part:
            continue
        node = {"gloss": part, "children": build_part_nodes(part, resolve_func)}
        children.append(node)
    return children


def render_tree(nodes):
    lines: list[str] = []

    def label_for(gloss):
        text = paraphrase_display(gloss)
        url = f"/glosses/{gloss.language}/{gloss.slug}/edit"
        return Markup(f'<a class="link link-primary" target="_blank" href="{url}">{text}</a>')

    def walk(node_list, prefix=""):
        total = len(node_list)
        for idx, node in enumerate(node_list):
            is_last = idx == total - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{label_for(node['gloss'])}")
            new_prefix = f"{prefix}{'    ' if is_last else '│   '}"
            if node["children"]:
                walk(node["children"], new_prefix)

    walk(nodes)
    return lines

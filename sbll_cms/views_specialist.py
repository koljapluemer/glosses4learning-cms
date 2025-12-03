from __future__ import annotations

from markupsafe import Markup
from flask import Blueprint, abort, render_template, request, redirect, url_for, flash
import json

from .storage import get_storage
from .language import get_language_store
from flask import current_app
from .utils import paraphrase_display
from .translation_tool import TranslationRequest, translate
from .gloss import Gloss
from .relations import attach_relation

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


@bp.route("/situations/<language>/<slug>", methods=["GET", "POST"])
def manage_situation(language: str, slug: str):
    storage = get_storage()
    situation = storage.load_gloss(language, slug)
    if not situation:
        abort(404)
    target_language = request.values.get("target_language") or ""
    native_language = request.values.get("native_language") or ""
    model = request.values.get("model") or "OpenAI|gpt-4o-mini"
    action = request.values.get("action") or ""

    def resolve(ref: str):
        return storage.resolve_reference(ref)

    root_nodes = []
    for ref in situation.children:
        gloss = resolve(ref)
        if not gloss or "eng:expression-goal" not in (gloss.tags or []):
            continue
        if native_language and gloss.language != native_language:
            continue
        node = {"gloss": gloss, "children": build_part_nodes(gloss, resolve)}
        root_nodes.append(node)

    tree_lines = render_tree(root_nodes, target_language=target_language, storage=storage)

    # Flatten nodes for translation table
    flat_glosses = dedupe_glosses(root_nodes)
    flat_glosses = [g for g in flat_glosses if not native_language or g.language == native_language]

    languages = get_language_store().list_languages()
    auto_results = []

    if request.method == "POST" and action:
        if action == "generate_auto":
            if not target_language:
                flash("Choose a target language before auto-translating.", "error")
            else:
                # find glosses missing translations in target lang
                candidates = [g for g in flat_glosses if not any(t.startswith(f"{target_language}:") for t in (g.translations or []))]
                settings = current_app.extensions["settings_store"].load()
                for gloss in candidates:
                    context = f"Situation: {situation.content}. Translate in the context of this situation."
                    if gloss.tags and any(tag.endswith("paraphrase") for tag in gloss.tags):
                        context += " This is a paraphrase; do not translate brackets literally—return how you would naturally express this."
                    req = TranslationRequest(
                        gloss=gloss,
                        target_language=target_language,
                        provider="OpenAI",
                        model=model.split("|", 1)[1],
                        context=context,
                    )
                    result = translate(req, settings, get_language_store())
                    auto_results.append({
                        "ref": f"{gloss.language}:{gloss.slug}",
                        "content": paraphrase_display(gloss),
                        "translations": result.translations or [],
                        "error": result.error,
                    })
        elif action == "accept_generated":
            payload = request.form.get("generated_payload") or ""
            selected = {s.strip() for s in request.form.getlist("selected_ref") if s.strip()}
            try:
                parsed = json.loads(payload)
            except Exception:
                parsed = []
            added = 0
            for entry in parsed:
                ref = (entry.get("ref") or "").strip()
                if ref not in selected:
                    continue
                translations = entry.get("translations") or []
                src = storage.resolve_reference(ref)
                if not src:
                    continue
                for t_text in translations:
                    existing = storage.find_gloss_by_content(target_language, t_text)
                    if existing:
                        target = existing
                    else:
                        target = storage.create_gloss(Gloss(content=t_text, language=target_language, tags=["machine-translation"]))
                    attach_relation(storage, src, "translations", target)
                    added += 1
            flash(f"Added {added} translations.", "success")
            return redirect(url_for("specialist.manage_situation", language=language, slug=slug, target_language=target_language, native_language=native_language))

    return render_template(
        "specialist/situation_manage.html",
        situation=situation,
        tree_lines=tree_lines,
        target_language=target_language,
        native_language=native_language,
        flat_glosses=flat_glosses,
        languages=languages,
        storage=storage,
        model=model,
        auto_results=auto_results,
    )


def build_part_nodes(gloss, resolve_func):
    children = []
    for ref in gloss.parts:
        part = resolve_func(ref)
        if not part:
            continue
        node = {"gloss": part, "children": build_part_nodes(part, resolve_func)}
        children.append(node)
    return children


def render_tree(nodes, target_language: str = "", storage=None):
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
            combined_children = list(node["children"])
            if target_language and storage:
                translations = [ref for ref in (node["gloss"].translations or []) if ref.startswith(f"{target_language}:")]
                for t_ref in translations:
                    t_gloss = storage.resolve_reference(t_ref)
                    if not t_gloss:
                        continue
                    combined_children.append({"gloss": t_gloss, "children": build_part_nodes(t_gloss, storage.resolve_reference)})
            if combined_children:
                walk(combined_children, new_prefix)

    walk(nodes)
    return lines


def resolve_parts(gloss):
    storage = get_storage()
    parts = []
    for ref in gloss.parts:
        part = storage.resolve_reference(ref)
        if part:
            parts.append(part)
    return parts


def dedupe_glosses(nodes):
    seen = set()
    ordered = []

    def walk(node_list):
        for node in node_list:
            gloss = node["gloss"]
            key = f"{gloss.language}:{gloss.slug}"
            if key not in seen:
                seen.add(key)
                ordered.append(gloss)
            if node.get("children"):
                walk(node["children"])

    walk(nodes)
    return ordered

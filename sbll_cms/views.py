from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from flask import Blueprint, flash, redirect, render_template, request, url_for

from .gloss import Gloss, RELATIONSHIP_FIELDS
from .storage import get_storage
from .utils import derive_slug, normalize_language_code, split_text_area

bp = Blueprint("glosses", __name__)


def _gloss_from_form() -> Gloss:
    content = (request.form.get("content") or "").strip()
    language = normalize_language_code(request.form.get("language"))
    transcriptions = split_text_area(request.form.get("transcriptions"))

    relationship_values = {
        field: split_text_area(request.form.get(field))
        for field in RELATIONSHIP_FIELDS
    }

    return Gloss(
        content=content,
        language=language,
        transcriptions=transcriptions,
        **relationship_values,
    )


def _validate_gloss(gloss: Gloss) -> list[str]:
    errors: list[str] = []
    if not gloss.content.strip():
        errors.append("Content is required.")
    slug = derive_slug(gloss.content)
    if not slug:
        errors.append("Content must include characters that produce a valid filename.")
    return errors


@bp.route("/")
def index():
    storage = get_storage()
    glosses = storage.list_glosses()
    grouped: dict[str, list[Gloss]] = defaultdict(list)
    for gloss in glosses:
        grouped[normalize_language_code(gloss.language)].append(gloss)
    sorted_languages = sorted(grouped.items(), key=lambda item: item[0])
    return render_template("index.html", grouped_glosses=sorted_languages)


@bp.route("/glosses/new", methods=["GET"])
def new_gloss():
    empty_gloss = Gloss(content="", language="und")
    return render_template("gloss_form.html", gloss=empty_gloss, mode="create", relationships=RELATIONSHIP_FIELDS)


@bp.route("/glosses", methods=["POST"])
def create_gloss():
    gloss = _gloss_from_form()
    errors = _validate_gloss(gloss)
    if errors:
        for message in errors:
            flash(message, "error")
        return render_template("gloss_form.html", gloss=gloss, mode="create", relationships=RELATIONSHIP_FIELDS), 400

    storage = get_storage()
    try:
        saved = storage.create_gloss(gloss)
    except FileExistsError as exc:
        flash(str(exc), "error")
        return render_template("gloss_form.html", gloss=gloss, mode="create", relationships=RELATIONSHIP_FIELDS), 409
    except ValueError as exc:
        flash(str(exc), "error")
        return render_template("gloss_form.html", gloss=gloss, mode="create", relationships=RELATIONSHIP_FIELDS), 400

    flash("Gloss created.", "success")
    return redirect(url_for("glosses.edit_gloss", language=saved.language, slug=saved.slug))


@bp.route("/glosses/<language>/<slug>/edit", methods=["GET"])
def edit_gloss(language: str, slug: str):
    storage = get_storage()
    gloss = storage.load_gloss(language, slug)
    if not gloss:
        flash("Gloss not found.", "error")
        return redirect(url_for("glosses.index")), 404
    return render_template("gloss_form.html", gloss=gloss, mode="edit", relationships=RELATIONSHIP_FIELDS)


@bp.route("/glosses/<language>/<slug>", methods=["POST"])
def update_gloss(language: str, slug: str):
    storage = get_storage()
    current = storage.load_gloss(language, slug)
    if not current:
        flash("Gloss not found.", "error")
        return redirect(url_for("glosses.index")), 404

    updated = _gloss_from_form()
    errors = _validate_gloss(updated)
    if errors:
        for message in errors:
            flash(message, "error")
        return render_template("gloss_form.html", gloss=updated, mode="edit", relationships=RELATIONSHIP_FIELDS), 400

    try:
        saved = storage.update_gloss(language, slug, updated)
    except FileExistsError as exc:
        flash(str(exc), "error")
        return render_template("gloss_form.html", gloss=updated, mode="edit", relationships=RELATIONSHIP_FIELDS), 409
    except (ValueError, FileNotFoundError) as exc:
        flash(str(exc), "error")
        return render_template("gloss_form.html", gloss=updated, mode="edit", relationships=RELATIONSHIP_FIELDS), 400

    flash("Gloss updated.", "success")
    return redirect(url_for("glosses.edit_gloss", language=saved.language, slug=saved.slug))


@bp.route("/glosses/<language>/<slug>/delete", methods=["POST"])
def delete_gloss(language: str, slug: str):
    storage = get_storage()
    storage.delete_gloss(language, slug)
    flash("Gloss deleted.", "success")
    return redirect(url_for("glosses.index"))

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

# Make sure local helpers and project modules are importable even with the hyphenated folder name.
HERE = Path(__file__).resolve()
APP_DIR = HERE.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

REPO_ROOT = next((p for p in HERE.parents if (p / "pyproject.toml").exists()), APP_DIR)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relations import RELATIONSHIP_FIELDS, WITHIN_LANGUAGE_RELATIONS, attach_relation, detach_relation, field_help_text, field_label, relation_rows  # type: ignore  # isort: skip
from src.shared.languages import load_language
from src.shared.log import configure_logging, get_logger
from src.shared.storage import Gloss, GlossStorage, derive_slug, normalize_language_code

configure_logging()
logger = get_logger(__name__)

app = Flask(__name__, template_folder="templates")
app.secret_key = "dev-secret"
app.config["TEMPLATES_AUTO_RELOAD"] = True

LANG_PATTERN = re.compile(r"^[a-z]{3}$")

storage = GlossStorage(REPO_ROOT / "data")


def _all_languages() -> list[dict[str, str]]:
    lang_dir = REPO_ROOT / "data" / "language"
    items: list[dict[str, str]] = []
    if not lang_dir.exists():
        return items
    for file in sorted(lang_dir.glob("*.json")):
        data = load_language(file.stem) or {}
        if data:
            items.append(
                {
                    "iso": str(data.get("isoCode", file.stem)).lower(),
                    "name": data.get("displayName") or data.get("name") or file.stem,
                    "symbol": data.get("symbol") or data.get("Symbol") or "",
                }
            )
    return items


def _validate_language(value: str | None) -> str:
    value = normalize_language_code(value or "")
    if not LANG_PATTERN.match(value):
        raise ValueError("Language must be a 3-letter ISO code.")
    if value == "und":
        raise ValueError("Language cannot be undefined.")
    return value


def _parse_transcriptions(raw: str | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in (raw or "").splitlines():
        if not line.strip():
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            result[key.strip()] = val.strip()
        else:
            result[line.strip()] = ""
    return result


def _load_gloss_or_404(language: str, slug: str) -> Gloss:
    gloss = storage.load_gloss(language, slug)
    if not gloss:
        abort(404)
    return gloss


def _grouped_glosses() -> list[tuple[str, list[Gloss]]]:
    grouped: dict[str, list[Gloss]] = {}
    for gloss in storage.list_glosses():
        grouped.setdefault(gloss.language, []).append(gloss)
    for glist in grouped.values():
        glist.sort(key=lambda g: g.content.lower())
    return sorted(grouped.items(), key=lambda pair: pair[0])


def _update_references(old_ref: str, new_ref: str) -> int:
    touched = 0
    for item in storage.list_glosses():
        changed = False
        for field in RELATIONSHIP_FIELDS:
            refs: list[str] = list(getattr(item, field, []) or [])
            if old_ref in refs:
                refs = [new_ref if ref == old_ref else ref for ref in refs]
                setattr(item, field, refs)
                changed = True
        if changed:
            storage.save_gloss(item)
            touched += 1
    return touched


def _render_relation_card(gloss: Gloss, field: str, message: str | None = None):
    rows = relation_rows(storage, gloss, field)
    return render_template(
        "relation_card.html",
        gloss=gloss,
        field=field,
        rows=rows,
        label=field_label(field),
        help_text=field_help_text(field),
        languages=_all_languages(),
        message=message,
        within_language=field in WITHIN_LANGUAGE_RELATIONS,
    )


@app.route("/")
def home():
    return redirect(url_for("list_glosses"))


@app.route("/glosses")
def list_glosses():
    return render_template("gloss_list.html", grouped_glosses=_grouped_glosses())


@app.route("/glosses/new", methods=["GET", "POST"])
def create_gloss():
    languages = _all_languages()
    default_lang = request.args.get("lang", "").strip().lower() or (languages[0]["iso"] if languages else "")
    form_language = default_lang
    form_content = ""
    form_transcriptions = ""
    if request.method == "POST":
        form_language = request.form.get("language", default_lang)
        form_content = request.form.get("content", "")
        form_transcriptions = request.form.get("transcriptions", "")
        try:
            language = _validate_language(form_language)
            content = form_content.strip()
            if not content:
                raise ValueError("Content is required.")
            gloss = Gloss(
                content=content,
                language=language,
                transcriptions=_parse_transcriptions(form_transcriptions),
                needsHumanCheck=request.form.get("needsHumanCheck") == "on",
                excludeFromLearning=request.form.get("excludeFromLearning") == "on",
            )
            gloss = storage.create_gloss(gloss)
            flash(f"Created gloss {language}:{gloss.slug}", "success")
            return redirect(url_for("edit_gloss", language=language, slug=gloss.slug))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Create gloss failed: %s", exc)
            flash(str(exc), "error")

    gloss = Gloss(content=form_content, language=form_language, transcriptions=_parse_transcriptions(form_transcriptions))
    return render_template(
        "gloss_form.html",
        gloss=gloss,
        mode="create",
        languages=languages,
    )


@app.route("/glosses/<language>/<slug>", methods=["GET", "POST"])
def edit_gloss(language: str, slug: str):
    gloss = _load_gloss_or_404(language, slug)
    if request.method == "POST":
        gloss.content = request.form.get("content", "").strip()
        gloss.transcriptions = _parse_transcriptions(request.form.get("transcriptions"))
        gloss.needsHumanCheck = request.form.get("needsHumanCheck") == "on"
        gloss.excludeFromLearning = request.form.get("excludeFromLearning") == "on"
        if not gloss.content:
            flash("Content is required.", "error")
        else:
            old_slug = gloss.slug or slug
            new_slug = derive_slug(gloss.content)
            old_ref = f"{gloss.language}:{old_slug}"
            new_ref = f"{gloss.language}:{new_slug}"

            if new_slug != old_slug:
                new_path = storage._path_for(gloss.language, new_slug)  # type: ignore[attr-defined]
                if new_path.exists():
                    flash("A gloss with this content already exists for this language.", "error")
                    return render_template(
                        "gloss_form.html",
                        gloss=gloss,
                        mode="edit",
                        languages=_all_languages(),
                        relation_fields=RELATIONSHIP_FIELDS,
                    )
                old_path = storage._path_for(gloss.language, old_slug)  # type: ignore[attr-defined]
                old_path.rename(new_path)
                gloss.slug = new_slug
                updated_refs = _update_references(old_ref, new_ref)
                flash(f"Saved. Updated {updated_refs} references after renaming.", "success")
            else:
                flash("Saved changes.", "success")
            storage.save_gloss(gloss)
            if request.form.get("next") == "list":
                return redirect(url_for("list_glosses"))
    return render_template(
        "gloss_form.html",
        gloss=gloss,
        mode="edit",
        languages=_all_languages(),
        relation_fields=RELATIONSHIP_FIELDS,
    )


@app.post("/glosses/<language>/<slug>/delete")
def delete_gloss(language: str, slug: str):
    gloss = _load_gloss_or_404(language, slug)
    target = storage._path_for(language, slug)  # type: ignore[attr-defined]
    target.unlink(missing_ok=True)  # type: ignore[attr-defined]

    removed_refs = 0
    for item in storage.list_glosses():
        changed = False
        for field in RELATIONSHIP_FIELDS:
            refs: list[str] = list(getattr(item, field, []) or [])
            filtered = [ref for ref in refs if ref != f"{language}:{slug}"]
            if len(filtered) != len(refs):
                setattr(item, field, filtered)
                changed = True
        if changed:
            removed_refs += 1
            storage.save_gloss(item)
    flash(f"Deleted gloss {language}:{slug}. Cleaned references in {removed_refs} glosses.", "success")
    return redirect(url_for("list_glosses"))


@app.get("/glosses/<language>/<slug>/relations/<field>")
def relation_card(language: str, slug: str, field: str):
    gloss = _load_gloss_or_404(language, slug)
    if field not in RELATIONSHIP_FIELDS:
        abort(404)
    return _render_relation_card(gloss, field)


@app.post("/glosses/<language>/<slug>/relations/<field>/add")
def add_relation(language: str, slug: str, field: str):
    gloss = _load_gloss_or_404(language, slug)
    if field not in RELATIONSHIP_FIELDS:
        abort(404)

    ref = request.form.get("ref", "").strip()
    content = request.form.get("content", "").strip()
    language_value = request.form.get("language", gloss.language)
    message = None

    try:
        if ref:
            target = storage.resolve_reference(ref)
            if not target:
                raise ValueError("No gloss found for that reference.")
        else:
            if not content:
                raise ValueError("Content is required to add a relationship.")
            target_language = gloss.language if field in WITHIN_LANGUAGE_RELATIONS else _validate_language(language_value)
            target = storage.ensure_gloss(target_language, content)
        attach_relation(storage, gloss, field, target)
        message = f"Attached {target.language}:{target.slug}."
    except Exception as exc:  # noqa: BLE001
        logger.warning("Attach relation failed: %s", exc)
        message = str(exc)

    return _render_relation_card(gloss, field, message=message)


@app.post("/glosses/<language>/<slug>/relations/<field>/remove")
def remove_relation(language: str, slug: str, field: str):
    gloss = _load_gloss_or_404(language, slug)
    if field not in RELATIONSHIP_FIELDS:
        abort(404)
    target_ref = request.form.get("ref", "").strip()
    message = None
    try:
        if not target_ref:
            raise ValueError("Missing relation reference.")
        detach_relation(storage, gloss, field, target_ref)
        message = "Relationship removed."
    except Exception as exc:  # noqa: BLE001
        logger.warning("Detach relation failed: %s", exc)
        message = str(exc)
    return _render_relation_card(gloss, field, message=message)


@app.get("/glosses/<language>/<slug>/relations/<field>/search")
def relation_search(language: str, slug: str, field: str):
    gloss = _load_gloss_or_404(language, slug)
    if field not in RELATIONSHIP_FIELDS:
        abort(404)
    query = (request.args.get("q") or request.args.get("content") or "").strip().lower()
    selected_language = request.args.get("language", gloss.language)
    try:
        chosen_language = gloss.language if field in WITHIN_LANGUAGE_RELATIONS else _validate_language(selected_language)
    except Exception:
        chosen_language = gloss.language

    current_refs = set(getattr(gloss, field, []) or [])
    suggestions = []
    if query:
        for candidate in storage.list_glosses():
            if candidate.language != chosen_language:
                continue
            if candidate.language == gloss.language and candidate.slug == gloss.slug:
                continue
            if f"{candidate.language}:{candidate.slug}" in current_refs:
                continue
            if query in candidate.content.lower():
                suggestions.append(candidate)
            if len(suggestions) >= 8:
                break

    return render_template(
        "relation_suggestions.html",
        suggestions=suggestions,
        field=field,
        base=gloss,
    )


if __name__ == "__main__":
    app.run(debug=True)

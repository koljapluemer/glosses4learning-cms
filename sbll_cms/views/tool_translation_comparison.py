from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for

from sbll_cms.entities.gloss import Gloss
from sbll_cms.storage import get_storage
from sbll_cms.views.blueprints import tools_bp


def _load_base_and_translations(language: str, slug: str, target_language: str):
    storage = get_storage()
    base = storage.load_gloss(language, slug)
    if not base:
        return None, []

    translation_refs = [ref for ref in (base.translations or []) if ref.startswith(f"{target_language}:")]
    translations = []
    for ref in translation_refs:
        t = storage.resolve_reference(ref)
        if not t:
            continue
        back_translations = []
        for bt_ref in (t.translations or []):
            if bt_ref.startswith(f"{base.language}:") and bt_ref != f"{base.language}:{base.slug}":
                bt_gloss = storage.resolve_reference(bt_ref)
                if bt_gloss:
                    back_translations.append(bt_gloss)
        note_glosses = []
        for n_ref in (t.notes or []):
            n_gloss = storage.resolve_reference(n_ref)
            if n_gloss and n_gloss.language == base.language:
                note_glosses.append(n_gloss)
        translations.append(
            {
                "ref": ref,
                "gloss": t,
                "back_translations": back_translations,
                "notes": note_glosses,
            }
        )
    return base, translations


@tools_bp.route("/translation-comparison/<language>/<slug>/<target_language>/manual", methods=["GET", "POST"])
def translation_comparison_manual(language: str, slug: str, target_language: str):
    storage = get_storage()
    base, translations = _load_base_and_translations(language, slug, target_language)
    if not base:
        flash("Gloss not found.", "error")
        return redirect(url_for("glosses.index")), 404

    if request.method == "POST":
        note_content = (request.form.get("note_content") or "").strip()
        translation_ref = request.form.get("translation_ref") or ""
        if note_content and translation_ref:
            translation = storage.resolve_reference(translation_ref)
            if translation:
                note = Gloss(content=note_content, language=base.language)
                try:
                    note = storage.create_gloss(note)
                except FileExistsError:
                    note = storage.ensure_gloss(base.language, note_content)
                note_ref = f"{note.language}:{note.slug}"
                if note_ref not in (translation.notes or []):
                    translation.notes.append(note_ref)
                    storage.save_gloss(translation)
                flash("Note added.", "success")
        return redirect(
            url_for(
                "tools.translation_comparison_manual",
                language=language,
                slug=slug,
                target_language=target_language,
            )
        )

    return render_template(
        "tool_translation_comparison/manual.html",
        base=base,
        target_language=target_language,
        translations=translations,
    )


@tools_bp.route("/translation-comparison/<language>/<slug>/<target_language>/input", methods=["GET"])
def translation_comparison_input(language: str, slug: str, target_language: str):
    base, _translations = _load_base_and_translations(language, slug, target_language)
    if not base:
        flash("Gloss not found.", "error")
        return redirect(url_for("glosses.index")), 404
    return render_template(
        "tool_translation_comparison/input_form.html",
        base=base,
        target_language=target_language,
    )


@tools_bp.route("/translation-comparison/<language>/<slug>/<target_language>/output", methods=["GET"])
def translation_comparison_output(language: str, slug: str, target_language: str):
    base, _translations = _load_base_and_translations(language, slug, target_language)
    if not base:
        flash("Gloss not found.", "error")
        return redirect(url_for("glosses.index")), 404
    return render_template(
        "tool_translation_comparison/output_form.html",
        base=base,
        target_language=target_language,
    )

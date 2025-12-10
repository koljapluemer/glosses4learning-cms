from __future__ import annotations

from flask import Request

from sbll_cms.entities.gloss.model import Gloss, RELATIONSHIP_FIELDS
from sbll_cms.utils.derive_slug import derive_slug
from sbll_cms.utils.normalize_language_code import normalize_language_code
from sbll_cms.utils.parse_key_value_lines import parse_key_value_lines
from sbll_cms.utils.split_text_area import split_text_area


def gloss_from_request(req: Request) -> Gloss:
    content = (req.form.get("content") or "").strip()
    language = normalize_language_code(req.form.get("language"))
    transcriptions = parse_key_value_lines(req.form.get("transcriptions"))

    relationship_values = {field: split_text_area(req.form.get(field)) for field in RELATIONSHIP_FIELDS}

    return Gloss(
        content=content,
        language=language,
        transcriptions=transcriptions,
        **relationship_values,
    )


def validate_gloss(gloss: Gloss) -> list[str]:
    errors: list[str] = []
    if not gloss.content.strip():
        errors.append("Content is required.")
    slug = derive_slug(gloss.content)
    if not slug:
        errors.append("Content must include characters that produce a valid filename.")
    try:
        normalize_language_code(gloss.language)
    except ValueError as exc:  # noqa: BLE001
        errors.append(str(exc))
    return errors

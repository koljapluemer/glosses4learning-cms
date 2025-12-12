from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.shared.storage import (
    Gloss,
    GlossStorage,
    RELATIONSHIP_FIELDS,
    WITHIN_LANGUAGE_RELATIONS,
    CROSS_LANGUAGE_RELATIONS,
    SYMMETRICAL_RELATIONS,
    attach_relation,
    derive_slug,
)

FIELD_LABELS = {
    "morphologically_related": "Morphologically related",
    "parts": "Parts",
    "has_similar_meaning": "Similar meaning",
    "sounds_similar": "Sounds similar",
    "usage_examples": "Usage examples",
    "to_be_differentiated_from": "Different from",
    "collocations": "Collocations",
    "typical_follow_up": "Typical follow up",
    "children": "Children",
    "translations": "Translations",
    "notes": "Notes",
    "tags": "Tags",
}

FIELD_HELP = {
    "translations": "Cross-language references. Pick the language first.",
    "notes": "Attach related notes in any language.",
    "tags": "Tags are glosses too; language is required.",
    "children": "Didactic children across languages.",
}


@dataclass
class RelationRow:
    ref: str
    iso: str
    slug: str
    title: str
    tags: list[str]
    missing: bool = False


def field_label(field: str) -> str:
    return FIELD_LABELS.get(field, field.replace("_", " ").title())


def field_help_text(field: str) -> str | None:
    return FIELD_HELP.get(field)


def parse_ref(ref: str, fallback_lang: str) -> tuple[str, str]:
    if ":" in ref:
        iso, slug = ref.split(":", 1)
    else:
        iso, slug = fallback_lang, ref
    return iso.strip().lower(), slug.strip()


def relation_rows(storage: GlossStorage, base: Gloss, field: str) -> list[RelationRow]:
    rows: list[RelationRow] = []
    for ref in getattr(base, field, []):
        iso, slug = parse_ref(ref, base.language)
        related = storage.resolve_reference(ref)
        rows.append(
            RelationRow(
                ref=ref,
                iso=iso,
                slug=slug,
                title=related.content if related else slug,
                tags=related.tags if related else [],
                missing=related is None,
            )
        )
    return rows


def detach_relation(storage: GlossStorage, base: Gloss, field: str, target_ref: str) -> None:
    """Detach a relationship between glosses (Flask UI only)."""
    if field not in RELATIONSHIP_FIELDS:
        raise ValueError(f"Unknown relation field: {field}")
    existing: list[str] = list(getattr(base, field, []) or [])
    if target_ref in existing:
        existing.remove(target_ref)
        setattr(base, field, existing)
        storage.save_gloss(base)

    if field in SYMMETRICAL_RELATIONS:
        _remove_symmetry(storage, base, field, target_ref)


def _remove_symmetry(storage: GlossStorage, base: Gloss, field: str, target_ref: str) -> None:
    target = storage.resolve_reference(target_ref)
    if not target:
        return
    back_ref = f"{base.language}:{base.slug or derive_slug(base.content)}"
    relations = getattr(target, field, []) or []
    if back_ref in relations:
        updated = [ref for ref in relations if ref != back_ref]
        setattr(target, field, updated)
        storage.save_gloss(target)

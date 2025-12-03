from __future__ import annotations

from .gloss import Gloss, RELATIONSHIP_FIELDS
from .storage import GlossStorage


def gloss_ref(gloss: Gloss) -> str:
    return f"{gloss.language}:{gloss.slug}"


def attach_relation(storage: GlossStorage, base: Gloss, field: str, target: Gloss) -> None:
    if field not in RELATIONSHIP_FIELDS:
        raise ValueError(f"Unknown relation field: {field}")

    ref = gloss_ref(target)
    relations = getattr(base, field)
    if ref not in relations:
        relations.append(ref)
        storage.save_gloss(base)

    if field == "translations":
        _ensure_translation_symmetry(storage, base, target)


def detach_relation(storage: GlossStorage, base: Gloss, field: str, target_ref: str) -> None:
    if field not in RELATIONSHIP_FIELDS:
        raise ValueError(f"Unknown relation field: {field}")

    relations = getattr(base, field)
    if target_ref in relations:
        relations.remove(target_ref)
        storage.save_gloss(base)

    if field == "translations":
        _remove_translation_symmetry(storage, base, target_ref)


def _ensure_translation_symmetry(storage: GlossStorage, base: Gloss, target: Gloss) -> None:
    back_ref = gloss_ref(base)
    target_relations = target.translations
    if back_ref not in target_relations:
        target_relations.append(back_ref)
        storage.save_gloss(target)


def _remove_translation_symmetry(storage: GlossStorage, base: Gloss, target_ref: str) -> None:
    target = storage.resolve_reference(target_ref)
    if not target:
        return
    back_ref = gloss_ref(base)
    translations = target.translations
    if back_ref in translations:
        translations.remove(back_ref)
        storage.save_gloss(target)

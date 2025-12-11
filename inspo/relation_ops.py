from __future__ import annotations

from sbll_cms.entities.gloss.model import Gloss, RELATIONSHIP_FIELDS
from sbll_cms.entities.gloss.relations import SYMMETRICAL_RELATIONS, WITHIN_LANGUAGE_RELATIONS
from sbll_cms.storage import GlossStorage


def gloss_ref(gloss: Gloss) -> str:
    return f"{gloss.language}:{gloss.slug}"


def attach_relation(storage: GlossStorage, base: Gloss, field: str, target: Gloss) -> None:
    if field not in RELATIONSHIP_FIELDS:
        raise ValueError(f"Unknown relation field: {field}")

    if field in WITHIN_LANGUAGE_RELATIONS and target.language != base.language:
        raise ValueError("Within-language relations must target the same language.")

    ref = gloss_ref(target)
    relations = getattr(base, field)
    if ref not in relations:
        relations.append(ref)
        storage.save_gloss(base)

    if field in SYMMETRICAL_RELATIONS:
        _ensure_symmetry(storage, base, target, field)


def detach_relation(storage: GlossStorage, base: Gloss, field: str, target_ref: str) -> None:
    if field not in RELATIONSHIP_FIELDS:
        raise ValueError(f"Unknown relation field: {field}")

    relations = getattr(base, field)
    if target_ref in relations:
        relations.remove(target_ref)
        storage.save_gloss(base)

    if field in SYMMETRICAL_RELATIONS:
        _remove_symmetry(storage, base, field, target_ref)


def _ensure_symmetry(storage: GlossStorage, base: Gloss, target: Gloss, field: str) -> None:
    back_ref = gloss_ref(base)
    target_relations = getattr(target, field)
    if back_ref not in target_relations:
        target_relations.append(back_ref)
        storage.save_gloss(target)


def _remove_symmetry(storage: GlossStorage, base: Gloss, field: str, target_ref: str) -> None:
    target = storage.resolve_reference(target_ref)
    if not target:
        return
    back_ref = gloss_ref(base)
    relations = getattr(target, field)
    if back_ref in relations:
        relations.remove(back_ref)
        storage.save_gloss(target)
from __future__ import annotations

from sbll_cms.storage import get_storage


def gloss_relation_rows(base, field: str):
    """Build rows for relation table rendering."""
    storage = get_storage()
    rows = []
    for ref in getattr(base, field):
        if ":" in ref:
            iso, slug = ref.split(":", 1)
        else:
            iso, slug = base.language, ref
        related = storage.resolve_reference(ref)
        tags = related.tags if related else []
        rows.append(
            {
                "ref": ref,
                "iso": iso,
                "slug": slug,
                "title": related.content if related else slug,
                "tags": tags,
            }
        )
    return rows
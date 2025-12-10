from __future__ import annotations

from flask import abort

from sbll_cms.entities.gloss import RELATIONSHIP_FIELDS


def require_relation_field(field: str) -> None:
    """Abort if the relation field is unknown."""
    if field not in RELATIONSHIP_FIELDS:
        abort(400)

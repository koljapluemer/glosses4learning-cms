from __future__ import annotations

from flask import abort

from sbll_cms.storage import get_storage


def load_gloss_or_404(language: str, slug: str):
    """Load a gloss by language/slug or abort with 404."""
    storage = get_storage()
    gloss = storage.load_gloss(language, slug)
    if not gloss:
        abort(404)
    return gloss

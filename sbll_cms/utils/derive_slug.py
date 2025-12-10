from __future__ import annotations

import sanitize_filename


def derive_slug(content: str) -> str:
    """Create a slug by removing characters that are illegal in filenames."""
    safe = sanitize_filename.sanitize(content).strip()
    encoded = safe.encode("utf-8")[:255]
    return encoded.decode("utf-8", "ignore")

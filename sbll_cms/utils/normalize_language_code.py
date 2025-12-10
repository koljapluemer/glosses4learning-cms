from __future__ import annotations

import re


LANGUAGE_PATTERN = re.compile(r"^[a-z]{3}$")


def normalize_language_code(language: str | None) -> str:
    """Ensure a 3-letter ISO code is always present; raise if missing/invalid."""
    if not language:
        raise ValueError("Language code is required.")
    language = language.strip().lower()
    if not LANGUAGE_PATTERN.match(language):
        raise ValueError("Language code must be a 3-letter ISO 639-3 string.")
    return language

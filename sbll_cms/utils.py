from __future__ import annotations

import re


INVALID_FILENAME_CHARS = r'[<>:"/\\\\|?*\x00-\x1F]'
INVALID_TRAILING = re.compile(r"[\\.\\s]+$")
LANGUAGE_PATTERN = re.compile(r"^[a-z]{3}$")


def derive_slug(content: str) -> str:
    """Create a slug by removing characters that are illegal in filenames."""
    slug = re.sub(INVALID_FILENAME_CHARS, "", content)
    slug = INVALID_TRAILING.sub("", slug.strip())
    return slug[:150]


def normalize_language_code(language: str | None) -> str:
    """Ensure a 3-letter ISO code is always present; default to 'und'."""
    if not language:
        return "und"
    language = language.strip().lower()
    if not LANGUAGE_PATTERN.match(language):
        return "und"
    return language


def split_text_area(value: str) -> list[str]:
    parts = [segment.strip() for segment in re.split(r"[\\r\\n,]+", value or "") if segment.strip()]
    return parts


def parse_key_value_lines(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in (value or "").splitlines():
        if not line.strip():
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            result[key.strip()] = val.strip()
        else:
            result[line.strip()] = ""
    return result

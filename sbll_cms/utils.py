from __future__ import annotations

import re
import sanitize_filename


LANGUAGE_PATTERN = re.compile(r"^[a-z]{3}$")


def derive_slug(content: str) -> str:
    """Create a slug by removing characters that are illegal in filenames."""
    safe = sanitize_filename.sanitize(content).strip()
    # Limit to 255 bytes to stay filesystem-friendly.
    encoded = safe.encode("utf-8")[:255]
    return encoded.decode("utf-8", "ignore")


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

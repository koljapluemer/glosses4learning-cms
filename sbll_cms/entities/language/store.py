from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from flask import current_app


@dataclass
class Language:
    iso_code: str
    display_name: str
    symbol: str
    ai_note: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Language":
        return cls(
            iso_code=data.get("isoCode", "").strip().lower(),
            display_name=data.get("displayName", "").strip(),
            symbol=data.get("symbol", "").strip(),
            ai_note=data.get("aiNote") or data.get("aiNote"),
        )


class LanguageStore:
    """Read-only store for languages defined on disk."""

    def __init__(self, language_root: Path):
        self.language_root = Path(language_root)
        self.language_root.mkdir(parents=True, exist_ok=True)

    def list_languages(self) -> list[Language]:
        languages: list[Language] = []
        if not self.language_root.exists():
            return languages

        for path in sorted(self.language_root.glob("*.json")):
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            languages.append(Language.from_dict(data))
        return languages

    def get(self, iso_code: str) -> Language | None:
        iso = (iso_code or "").strip().lower()
        path = self.language_root / f"{iso}.json"
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return Language.from_dict(data)


def get_language_store() -> LanguageStore:
    return current_app.extensions["language_store"]

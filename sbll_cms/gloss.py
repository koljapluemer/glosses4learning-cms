from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .utils import normalize_language_code


RELATIONSHIP_FIELDS = [
    "morphologically_related",
    "parts",
    "has_similar_meaning",
    "sounds_similar",
    "usage_examples",
    "to_be_differentiated_from",
    "collocations",
    "typical_follow_up",
    "children",
    "translations",
    "notes",
    "tags",
]


@dataclass
class Gloss:
    content: str
    language: str = "und"
    transcriptions: dict[str, str] = field(default_factory=dict)
    morphologically_related: list[str] = field(default_factory=list)
    parts: list[str] = field(default_factory=list)
    has_similar_meaning: list[str] = field(default_factory=list)
    sounds_similar: list[str] = field(default_factory=list)
    usage_examples: list[str] = field(default_factory=list)
    to_be_differentiated_from: list[str] = field(default_factory=list)
    collocations: list[str] = field(default_factory=list)
    typical_follow_up: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)
    translations: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    slug: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], slug: str | None = None, language: str | None = None) -> "Gloss":
        return cls(
            content=data.get("content", ""),
            language=normalize_language_code(language or data.get("language", "und")),
            transcriptions=dict(data.get("transcriptions", {}) or {}),
            morphologically_related=list(data.get("morphologically_related", []) or []),
            parts=list(data.get("parts", []) or []),
            has_similar_meaning=list(data.get("has_similar_meaning", []) or []),
            sounds_similar=list(data.get("sounds_similar", []) or []),
            usage_examples=list(data.get("usage_examples", []) or []),
            to_be_differentiated_from=list(data.get("to_be_differentiated_from", []) or []),
            collocations=list(data.get("collocations", []) or []),
            typical_follow_up=list(data.get("typical_follow_up", []) or []),
            children=list(data.get("children", []) or []),
            translations=list(data.get("translations", []) or []),
            notes=list(data.get("notes", []) or []),
            tags=list(data.get("tags", []) or []),
            slug=slug,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "language": normalize_language_code(self.language),
            "transcriptions": self.transcriptions,
            "morphologically_related": self.morphologically_related,
            "parts": self.parts,
            "has_similar_meaning": self.has_similar_meaning,
            "sounds_similar": self.sounds_similar,
            "usage_examples": self.usage_examples,
            "to_be_differentiated_from": self.to_be_differentiated_from,
            "collocations": self.collocations,
            "typical_follow_up": self.typical_follow_up,
            "children": self.children,
            "translations": self.translations,
            "notes": self.notes,
            "tags": self.tags,
        }

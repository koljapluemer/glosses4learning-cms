from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .utils import normalize_language_code


RELATIONSHIP_FIELDS = [
    "contains",
    "near_synonyms",
    "near_homophones",
    "translations",
    "clarifies_usage",
    "to_be_differentiated_from",
    "collocations",
]


@dataclass
class Gloss:
    content: str
    language: str = "und"
    transcriptions: list[str] = field(default_factory=list)
    contains: list[str] = field(default_factory=list)
    near_synonyms: list[str] = field(default_factory=list)
    near_homophones: list[str] = field(default_factory=list)
    translations: list[str] = field(default_factory=list)
    clarifies_usage: list[str] = field(default_factory=list)
    to_be_differentiated_from: list[str] = field(default_factory=list)
    collocations: list[str] = field(default_factory=list)
    slug: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], slug: str | None = None, language: str | None = None) -> "Gloss":
        return cls(
            content=data.get("content", ""),
            language=normalize_language_code(language or data.get("language", "und")),
            transcriptions=list(data.get("transcriptions", []) or []),
            contains=list(data.get("contains", []) or []),
            near_synonyms=list(data.get("near_synonyms", []) or []),
            near_homophones=list(data.get("near_homophones", []) or []),
            translations=list(data.get("translations", []) or []),
            clarifies_usage=list(data.get("clarifies_usage", []) or []),
            to_be_differentiated_from=list(data.get("to_be_differentiated_from", []) or []),
            collocations=list(data.get("collocations", []) or []),
            slug=slug,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "language": normalize_language_code(self.language),
            "transcriptions": self.transcriptions,
            "contains": self.contains,
            "near_synonyms": self.near_synonyms,
            "near_homophones": self.near_homophones,
            "translations": self.translations,
            "clarifies_usage": self.clarifies_usage,
            "to_be_differentiated_from": self.to_be_differentiated_from,
            "collocations": self.collocations,
        }

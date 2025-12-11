from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.shared.log import get_logger

logger = get_logger(__name__)


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


def normalize_language_code(code: str | None) -> str:
    return (code or "").strip().lower()


def derive_slug(text: str) -> str:
    """
    Build a filesystem-safe slug while preserving Unicode.
    - Remove characters illegal on common filesystems: / \ ? * : | " < >
    - Remove control chars
    - Trim trailing dot/space (Windows)
    - Truncate to a safe length (120 chars)
    """
    text = text or ""
    text = re.sub(r'[\\/\?\*\|":<>]', "", text)
    text = "".join(ch for ch in text if ord(ch) >= 32)
    text = text.rstrip(" .")
    if len(text) > 120:
        text = text[:120].rstrip(" .")
    if not text:
        raise ValueError("Content must produce a valid slug.")
    return text


@dataclass
class Gloss:
    content: str
    language: str = "und"
    transcriptions: dict[str, str] = field(default_factory=dict)
    logs: dict[str, str] = field(default_factory=dict)
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
            logs=dict(data.get("logs", {}) or {}),
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
            "logs": self.logs,
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


class GlossStorage:
    """File-system backed storage pointing to data/ and situations/ roots."""

    def __init__(self, data_root: Path, situations_root: Path | None = None):
        self.data_root = Path(data_root)
        self.situations_root = Path(situations_root) if situations_root else self.data_root / "situations"
        self.gloss_root = self.data_root / "gloss"
        if not self.gloss_root.exists():
            raise FileNotFoundError(f"Gloss directory not found: {self.gloss_root}")

    def _language_dir(self, language: str) -> Path:
        lang = normalize_language_code(language)
        target = self.gloss_root / lang
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _path_for(self, language: str, slug: str) -> Path:
        return self._language_dir(language) / f"{slug}.json"

    def list_glosses(self) -> list[Gloss]:
        glosses: list[Gloss] = []
        if not self.gloss_root.exists():
            return glosses
        for language_dir in sorted(self.gloss_root.iterdir()):
            if not language_dir.is_dir():
                continue
            for gloss_file in sorted(language_dir.glob("*.json")):
                with gloss_file.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                gloss = Gloss.from_dict(data, slug=gloss_file.stem, language=language_dir.name)
                glosses.append(gloss)
        return glosses

    def load_gloss(self, language: str, slug: str) -> Gloss | None:
        path = self._path_for(language, slug)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return Gloss.from_dict(data, slug=slug, language=language)

    def find_gloss_by_content(self, language: str, content: str) -> Gloss | None:
        language = normalize_language_code(language)
        try:
            slug = derive_slug(content)
        except Exception:
            return None
        return self.load_gloss(language, slug)

    def resolve_reference(self, ref: str) -> Gloss | None:
        if ":" not in ref:
            return None
        language, slug = ref.split(":", 1)
        language = normalize_language_code(language)
        slug = slug.strip()
        if not slug:
            return None
        return self.load_gloss(language, slug)

    def ensure_gloss(self, language: str, content: str) -> Gloss:
        language = normalize_language_code(language)
        existing = self.find_gloss_by_content(language, content)
        if existing:
            return existing
        new_gloss = Gloss(content=content, language=language)
        return self.create_gloss(new_gloss)

    def create_gloss(self, gloss: Gloss) -> Gloss:
        slug = derive_slug(gloss.content)
        language = normalize_language_code(gloss.language)
        target = self._path_for(language, slug)
        if target.exists():
            raise FileExistsError(f"Gloss already exists: {language}:{slug}")
        self._write_gloss(target, gloss)
        gloss.slug = slug
        gloss.language = language
        logger.info("Created gloss %s:%s", language, slug)
        return gloss

    def save_gloss(self, gloss: Gloss) -> Gloss:
        if not gloss.slug or not gloss.language:
            raise ValueError("Gloss must have language and slug before saving.")
        target = self._path_for(gloss.language, gloss.slug)
        self._write_gloss(target, gloss)
        return gloss

    def _write_gloss(self, path: Path, gloss: Gloss) -> None:
        payload = gloss.to_dict()
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)


def attach_relation(storage: GlossStorage, source: Gloss, field: str, target: Gloss) -> None:
    if field not in RELATIONSHIP_FIELDS:
        raise ValueError(f"Unknown relationship field: {field}")
    refs = getattr(source, field, []) or []
    ref = f"{target.language}:{target.slug or derive_slug(target.content)}"
    if ref not in refs:
        refs = list(refs) + [ref]
        setattr(source, field, refs)
        storage.save_gloss(source)

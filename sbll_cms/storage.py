from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Iterator

from flask import current_app

from sbll_cms.entities.gloss import Gloss
from sbll_cms.utils.derive_slug import derive_slug
from sbll_cms.utils.normalize_language_code import normalize_language_code


class GlossStorage:
    """File-system backed storage that treats data/ as the single source of truth."""

    def __init__(self, data_root: Path):
        self.data_root = Path(data_root)
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.gloss_root = self.data_root / "gloss"
        self.gloss_root.mkdir(parents=True, exist_ok=True)

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

    def create_gloss(self, gloss: Gloss) -> Gloss:
        slug = derive_slug(gloss.content)
        if not slug:
            raise ValueError("Content must produce a valid slug.")

        language = normalize_language_code(gloss.language)
        target = self._path_for(language, slug)
        if target.exists():
            raise FileExistsError(f"A gloss already exists for {language}:{slug}")

        self._write_gloss(target, gloss)
        gloss.slug = slug
        gloss.language = language
        return gloss

    def save_gloss(self, gloss: Gloss) -> Gloss:
        if not gloss.slug or not gloss.language:
            raise ValueError("Gloss must have language and slug before saving.")
        target = self._path_for(gloss.language, gloss.slug)
        self._write_gloss(target, gloss)
        return gloss

    def update_gloss(self, original_language: str, original_slug: str, gloss: Gloss) -> Gloss:
        language = normalize_language_code(gloss.language)
        slug = derive_slug(gloss.content)
        if not slug:
            raise ValueError("Content must produce a valid slug.")

        target = self._path_for(language, slug)
        original_path = self._path_for(original_language, original_slug)
        if not original_path.exists():
            raise FileNotFoundError(f"Original gloss {original_language}:{original_slug} missing.")

        if (language != original_language or slug != original_slug) and target.exists():
            raise FileExistsError(f"A gloss already exists for {language}:{slug}")

        # If core identity changed, perform rename/refactor.
        if language != original_language or slug != original_slug:
            return self.rename_gloss(original_language, original_slug, language, slug, gloss)

        self._write_gloss(target, gloss)
        gloss.slug = slug
        gloss.language = language
        return gloss

    def delete_gloss(self, language: str, slug: str) -> None:
        path = self._path_for(language, slug)
        if path.exists():
            path.unlink()

    def _write_gloss(self, path: Path, gloss: Gloss) -> None:
        payload = gloss.to_dict()
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)

    def rename_gloss(self, old_language: str, old_slug: str, new_language: str, new_slug: str, gloss: Gloss) -> Gloss:
        """Rename gloss file and rewrite all references in the dataset."""
        old_language = normalize_language_code(old_language)
        new_language = normalize_language_code(new_language)
        old_ref = f"{old_language}:{old_slug}"
        new_ref = f"{new_language}:{new_slug}"

        # Save new file first.
        new_path = self._path_for(new_language, new_slug)
        if new_path.exists() and (new_language != old_language or new_slug != old_slug):
            raise FileExistsError(f"Target gloss already exists: {new_language}:{new_slug}")

        gloss.language = new_language
        gloss.slug = new_slug
        self._write_gloss(new_path, gloss)

        # Remove old file if different.
        old_path = self._path_for(old_language, old_slug)
        if old_path.exists() and old_path != new_path:
            old_path.unlink()

        # Rewrite references across all glosses.
        from sbll_cms.entities.gloss import RELATIONSHIP_FIELDS  # local import to avoid cycle

        for item in self.list_glosses():
            changed = False
            for field in RELATIONSHIP_FIELDS:
                refs = getattr(item, field)
                if not isinstance(refs, list):
                    continue
                if old_ref in refs:
                    # avoid duplication if new_ref already present
                    if new_ref not in refs:
                        refs = [new_ref if ref == old_ref else ref for ref in refs]
                    else:
                        refs = [ref for ref in refs if ref != old_ref]
                    setattr(item, field, refs)
                    changed = True
            if changed:
                self.save_gloss(item)

        return gloss

    def find_gloss_by_content(self, language: str, content: str) -> Gloss | None:
        language = normalize_language_code(language)
        slug = derive_slug(content)
        if not slug:
            return None
        return self.load_gloss(language, slug)

    def ensure_gloss(self, language: str, content: str) -> Gloss:
        existing = self.find_gloss_by_content(language, content)
        if existing:
            return existing
        new_gloss = Gloss(content=content, language=language)
        return self.create_gloss(new_gloss)

    def resolve_reference(self, ref: str) -> Gloss | None:
        if ":" not in ref:
            return None
        language, slug = ref.split(":", 1)
        language = normalize_language_code(language)
        slug = slug.strip()
        if not slug:
            return None
        return self.load_gloss(language, slug)

    def search_glosses(self, query: str, language: str | None = None, limit: int = 10) -> list[Gloss]:
        query = (query or "").strip().lower()
        language = normalize_language_code(language) if language else ""
        if not query:
            return []

        results: list[Gloss] = []
        for gloss in self.list_glosses():
            if language and gloss.language != language:
                continue
            if query in gloss.content.lower() or query in (gloss.slug or "").lower():
                results.append(gloss)
            if len(results) >= limit:
                break
        return results


def get_storage() -> GlossStorage:
    return current_app.extensions["gloss_storage"]

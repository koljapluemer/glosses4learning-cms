from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from flask import current_app

from .gloss import Gloss
from .utils import derive_slug, normalize_language_code


class GlossStorage:
    """File-system backed storage that treats data/ as the single source of truth."""

    def __init__(self, data_root: Path):
        self.data_root = Path(data_root)
        self.data_root.mkdir(parents=True, exist_ok=True)

    def _language_dir(self, language: str) -> Path:
        lang = normalize_language_code(language)
        target = self.data_root / lang
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _path_for(self, language: str, slug: str) -> Path:
        return self._language_dir(language) / f"{slug}.json"

    def list_glosses(self) -> list[Gloss]:
        glosses: list[Gloss] = []
        if not self.data_root.exists():
            return glosses

        for language_dir in sorted(self.data_root.iterdir()):
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

        self._write_gloss(target, gloss)
        if target != original_path and original_path.exists():
            original_path.unlink()

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


def get_storage() -> GlossStorage:
    return current_app.extensions["gloss_storage"]

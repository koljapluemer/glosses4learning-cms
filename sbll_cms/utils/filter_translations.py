from __future__ import annotations


def filter_translations(translations: list[str] | None, target_language: str | None) -> list[str]:
    if not translations or not target_language:
        return []
    target_language = target_language.strip().lower()
    return [ref for ref in translations if ref.lower().startswith(f"{target_language}:")]

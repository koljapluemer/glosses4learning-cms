from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import requests

from sbll_cms.entities.gloss import Gloss
from sbll_cms.entities.language import LanguageStore
from .settings import Settings


@dataclass
class TranslationRequest:
    gloss: Gloss
    target_language: str
    provider: str
    model: str | None = None
    context: str | None = None


@dataclass
class TranslationResult:
    translations: list[str] | None
    error: str | None = None
    provider: str | None = None
    model: str | None = None


SUPPORTED_MODELS = [
    ("OpenAI", "gpt-4o-mini"),
    ("OpenAI", "gpt-4.1"),
]


def translate(req: TranslationRequest, settings: Settings, language_store: LanguageStore) -> TranslationResult:
    provider = req.provider
    model = req.model

    ai_note = ""
    target_lang_obj = language_store.get(req.target_language)
    if target_lang_obj and getattr(target_lang_obj, "aiNote", None):
        ai_note = target_lang_obj.ai_note

    key = settings.api_keys.openai
    if not key:
        return TranslationResult(translations=None, error="OpenAI API key not set.", provider=provider, model=model)
    return _translate_openai(req, key, ai_note)


def _translate_openai(req: TranslationRequest, api_key: str, ai_note: str) -> TranslationResult:
    is_paraphrase = req.context and "[paraphrase]" in req.context
    if is_paraphrase:
        prompt = (
            f"Imagine the learner wants to '{req.gloss.content}' in {req.target_language}. "
            "Return multiple natural options on how to do this. "
            "Return a JSON object with a 'translations' array expressions."
        )
    else:
        prompt = (
            f"Translate the following gloss into {req.target_language}. "
            "Return a JSON object with a 'translations' array of translation strings. Keep them concise."
        )
    if ai_note:
        prompt += f" Notes for this language: {ai_note}."
    if req.context:
        prompt += f" Additional context: {req.context}"
    prompt += f" Gloss: {req.gloss.content}"
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": req.model or "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a concise translation assistant for language learning glosses."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 200,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "translation_list",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "translations": {"type": "array", "items": {"type": "string"}}
                            },
                            "required": ["translations"],
                            "additionalProperties": False,
                        },
                        "strict": True,
                    },
                },
            },
            timeout=30,
        )
        data = response.json()
        if response.status_code != 200:
            return TranslationResult(translations=None, error=data.get("error", {}).get("message", "OpenAI error"), provider="OpenAI", model=req.model)
        content = data["choices"][0]["message"]["content"].strip()
        translations = []
        try:
            parsed = json.loads(content)
            translations = _extract_translations(parsed)
        except Exception:
            translations = _extract_translations(content)
        translations = [t for t in translations if t.strip()]
        return TranslationResult(translations=translations, provider="OpenAI", model=req.model)
    except Exception as exc:  # noqa: BLE001
        return TranslationResult(translations=None, error=str(exc), provider="OpenAI", model=req.model)


def _extract_translations(obj: Any) -> list[str]:
    results: list[str] = []
    if obj is None:
        return results
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, list):
        for item in obj:
            results.extend(_extract_translations(item))
        return results
    if isinstance(obj, dict):
        if "translations" in obj and isinstance(obj["translations"], list):
            results.extend(_extract_translations(obj["translations"]))
        else:
            for value in obj.values():
                results.extend(_extract_translations(value))
    return results

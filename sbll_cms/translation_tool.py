from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests

from .gloss import Gloss
from .language import LanguageStore
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
    translation: str | None
    error: str | None = None
    provider: str | None = None
    model: str | None = None


SUPPORTED_MODELS = [
    ("OpenAI", "gpt-4o-mini"),
    ("OpenAI", "gpt-4.1"),
    ("DeepL", "general"),
]


def translate(req: TranslationRequest, settings: Settings, language_store: LanguageStore) -> TranslationResult:
    provider = req.provider
    model = req.model

    ai_note = ""
    target_lang_obj = language_store.get(req.target_language)
    if target_lang_obj and getattr(target_lang_obj, "ai_note", None):
        ai_note = target_lang_obj.ai_note

    if provider == "OpenAI":
        key = settings.api_keys.openai or os.getenv("OPENAI_API_KEY")
        if not key:
            return TranslationResult(translation=None, error="OpenAI API key not set.", provider=provider, model=model)
        return _translate_openai(req, key, ai_note)
    if provider == "DeepL":
        key = settings.api_keys.deepl or os.getenv("DEEPL_API_KEY")
        if not key:
            return TranslationResult(translation=None, error="DeepL API key not set.", provider=provider, model=model)
        return _translate_deepl(req, key, ai_note)
    return TranslationResult(translation=None, error="Unsupported provider.", provider=provider, model=model)


def _translate_openai(req: TranslationRequest, api_key: str, ai_note: str) -> TranslationResult:
    prompt = f"Translate the following gloss into {req.target_language}. Keep it concise.\n"
    if ai_note:
        prompt += f"Notes for this language: {ai_note}\n"
    if req.context:
        prompt += f"Additional context: {req.context}\n"
    prompt += f"Gloss: {req.gloss.content}"
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
                "max_tokens": 100,
            },
            timeout=30,
        )
        data = response.json()
        if response.status_code != 200:
            return TranslationResult(translation=None, error=data.get("error", {}).get("message", "OpenAI error"), provider="OpenAI", model=req.model)
        text = data["choices"][0]["message"]["content"].strip()
        return TranslationResult(translation=text, provider="OpenAI", model=req.model)
    except Exception as exc:  # noqa: BLE001
        return TranslationResult(translation=None, error=str(exc), provider="OpenAI", model=req.model)


def _translate_deepl(req: TranslationRequest, api_key: str, ai_note: str) -> TranslationResult:
    prompt = req.gloss.content
    if not req.target_language:
        return TranslationResult(translation=None, error="Target language missing.", provider="DeepL", model="general")
    target_lang = req.target_language.upper()
    try:
        response = requests.post(
            "https://api-free.deepl.com/v2/translate",
            data={
                "text": prompt,
                "target_lang": target_lang,
                "formality": "default",
            },
            headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
            timeout=30,
        )
        data = response.json()
        if response.status_code != 200:
            message = data.get("message") or data.get("error", "DeepL error")
            return TranslationResult(translation=None, error=message, provider="DeepL", model="general")
        text = data["translations"][0]["text"]
        return TranslationResult(translation=text, provider="DeepL", model="general")
    except Exception as exc:  # noqa: BLE001
        return TranslationResult(translation=None, error=str(exc), provider="DeepL", model="general")

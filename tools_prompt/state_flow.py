from __future__ import annotations

from pathlib import Path
from typing import Any

from prompt_toolkit.shortcuts import choice

from tools_prompt.common import load_json, save_json
from tools_tk.shared.gloss_storage import GlossStorage

STATE_FILE = Path(__file__).resolve().parent / "state.json"


def load_state() -> dict[str, Any]:
    return load_json(STATE_FILE)


def save_state(state: dict[str, Any]) -> None:
    save_json(STATE_FILE, state)


def pick_situation(storage: GlossStorage):
    glosses = storage.list_glosses()
    situations = [g for g in glosses if "eng:situation" in (g.tags or [])]
    if not situations:
        return None
    values = [(f"{g.language}:{g.slug}", f"{g.content} [{g.language}:{g.slug}]") for g in situations]
    return choice(message="Select situation", options=values, default=values[0][0] if values else None)


def pick_language(title: str, languages: list[str]):
    values = [(lang, lang) for lang in languages]
    return choice(message=title, options=values, default=values[0][0] if values else None)


def set_situation_flow(storage: GlossStorage) -> dict[str, Any] | None:
    glosses = storage.list_glosses()
    langs = sorted({g.language for g in glosses})
    situation_ref = pick_situation(storage)
    if not situation_ref:
        return None
    native_language = pick_language("Select native language", langs)
    target_language = pick_language("Select target language", langs)
    if not native_language or not target_language:
        return None
    state = {
        "situation_ref": situation_ref,
        "native_language": native_language,
        "target_language": target_language,
    }
    save_state(state)
    return state

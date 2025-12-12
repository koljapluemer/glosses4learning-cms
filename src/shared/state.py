from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict


class AppState(TypedDict, total=False):
    situation_ref: str
    native_language: str
    target_language: str
    settings: dict[str, Any]


STATE_FILE = Path(__file__).resolve().parent / "state.json"


def load_state() -> AppState:
    if not STATE_FILE.exists():
        return AppState()
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return AppState(**data)
    except Exception:
        return AppState()
    return AppState()


def save_state(state: AppState) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def get_api_key() -> str:
    """
    Return the OpenAI API key from the local state file.

    The key is managed via the TUI settings flow (flow_set_settings.py) and
    stored under settings.OPENAI_API_KEY in state.json. No environment
    variables or CLI overrides are considered here.
    """
    state = load_state()
    settings = state.get("settings") or {}
    api_key = settings.get("OPENAI_API_KEY")
    if not api_key or not isinstance(api_key, str):
        raise ValueError(
            "OPENAI_API_KEY not found in state. "
            "Run the settings flow to configure it (TUI Settings)."
        )
    return api_key.strip()

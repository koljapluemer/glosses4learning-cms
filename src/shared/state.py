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

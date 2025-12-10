from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict


class State(TypedDict, total=False):
    situation_ref: str
    native_language: str
    target_language: str


DEFAULT_STATE: State = {}


def state_path(base_dir: Path) -> Path:
    return Path(base_dir) / "state.json"


def load_state(base_dir: Path) -> State:
    path = state_path(base_dir)
    if not path.exists():
        return DEFAULT_STATE.copy()
    try:
        data = json.loads(path.read_text())
        if isinstance(data, dict):
            return State(**data)
    except Exception:
        pass
    return DEFAULT_STATE.copy()


def save_state(base_dir: Path, data: State) -> None:
    path = state_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

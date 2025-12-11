from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
LANG_DIR = REPO_ROOT / "data" / "language"


def load_language(code: str) -> dict[str, Any] | None:
    code = (code or "").strip().lower()
    path = LANG_DIR / f"{code}.json"
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return None


def get_ai_note(code: str) -> str:
    data = load_language(code) or {}
    return str(data.get("aiNote") or data.get("ai_note") or "").strip()

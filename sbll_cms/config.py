from __future__ import annotations

import os
from pathlib import Path


class Config:
    """Default Flask configuration for the glossary CMS."""

    SECRET_KEY = os.getenv("SBLL_SECRET_KEY", "dev-secret-key")
    DATA_ROOT = Path(os.getenv("SBLL_DATA_ROOT", Path(__file__).resolve().parent.parent / "data"))
    JSON_SORT_KEYS = False

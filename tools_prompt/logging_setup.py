from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(level: int = logging.INFO) -> Path:
    """
    Configure root logger for the prompt tools.
    Writes to tools_prompt/prompt.log to avoid polluting TUI stdout.
    """
    log_path = Path(__file__).resolve().parent / "prompt.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    if root.handlers:
        return log_path
    handler = logging.FileHandler(log_path, encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(fmt)
    root.setLevel(level)
    root.addHandler(handler)
    return log_path

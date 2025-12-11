from __future__ import annotations

import logging
from pathlib import Path


LOG_DIR = Path(__file__).resolve().parent / "log_files"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"


def configure_logging(level: int = logging.INFO) -> Path:
    """
    Configure a file-based logger for the CLI/flows to avoid polluting stdout.
    Returns the log file path.
    """
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        handler.setFormatter(fmt)
        root.setLevel(level)
        root.addHandler(handler)
    return LOG_FILE


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)

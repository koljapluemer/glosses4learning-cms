"""Structured logging configuration for agent operations."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from agent.config import AGENT_LOG_DIR


class AgentLogFormatter(logging.Formatter):
    """
    JSON formatter for structured agent logs.

    Outputs logs as JSON with structured fields for easy parsing and analysis.
    Each log entry includes timestamp, level, logger name, message, and optional
    contextual fields like tool name, operation, and gloss/situation references.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: LogRecord to format

        Returns:
            JSON string representation of the log entry
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "tool": getattr(record, "tool", None),
            "operation": getattr(record, "operation", None),
            "gloss_ref": getattr(record, "gloss_ref", None),
            "situation_ref": getattr(record, "situation_ref", None),
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Remove None values for cleaner output
        log_entry = {k: v for k, v in log_entry.items() if v is not None}

        return json.dumps(log_entry, ensure_ascii=False)


class LogContext:
    """
    Context manager for adding structured context to logs.

    Temporarily adds contextual fields (like tool, gloss_ref) to all log records
    within the context. This avoids manually passing context to every log call.

    Example:
        >>> with LogContext(logger, tool="add_translation", gloss_ref="eng:hello"):
        ...     logger.info("Adding translation")  # Will include tool and gloss_ref
    """

    def __init__(self, logger: logging.Logger, **kwargs: Any):
        """
        Initialize log context.

        Args:
            logger: Logger to add context to
            **kwargs: Contextual fields to add to log records
        """
        self.logger = logger
        self.context = kwargs
        self.old_factory = None

    def __enter__(self) -> logging.Logger:
        """Enter context and install custom log record factory."""
        # Store old factory
        self.old_factory = logging.getLogRecordFactory()

        # Create new factory with context
        def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        return self.logger

    def __exit__(self, *args: Any) -> None:
        """Exit context and restore original log record factory."""
        if self.old_factory:
            logging.setLogRecordFactory(self.old_factory)


def setup_agent_logging(session_id: str | None = None) -> logging.Logger:
    """
    Setup persistent logging for agent operations.

    Creates two log files:
    - agent_YYYYMMDD.log: Daily rotating log
    - agent_session_<session_id>.log: Per-session log

    Both files use JSON format for structured logging. Console output
    uses human-readable format for easier development debugging.

    Args:
        session_id: Optional session ID (defaults to timestamp)

    Returns:
        Configured logger instance

    Example:
        >>> logger = setup_agent_logging()
        >>> logger.info("Agent started")
        >>> with LogContext(logger, tool="add_gloss"):
        ...     logger.info("Creating gloss")
    """
    # Generate session ID if not provided
    if session_id is None:
        session_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    # Ensure log directory exists
    AGENT_LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Create logger
    logger = logging.getLogger("agent")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()  # Remove any existing handlers

    # Daily rotating log (JSON format)
    daily_log_path = AGENT_LOG_DIR / f"agent_{datetime.utcnow().strftime('%Y%m%d')}.log"
    daily_handler = logging.FileHandler(daily_log_path, encoding="utf-8")
    daily_handler.setFormatter(AgentLogFormatter())
    logger.addHandler(daily_handler)

    # Session-specific log (JSON format)
    session_log_path = AGENT_LOG_DIR / f"agent_session_{session_id}.log"
    session_handler = logging.FileHandler(session_log_path, encoding="utf-8")
    session_handler.setFormatter(AgentLogFormatter())
    logger.addHandler(session_handler)

    # Console handler (human-readable format)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(console_handler)

    # Log initialization
    logger.info(f"Agent logging initialized. Session: {session_id}")

    return logger

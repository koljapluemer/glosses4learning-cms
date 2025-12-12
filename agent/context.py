"""Agent execution context shared across all tools."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from src.shared.storage import GlossStorage


@dataclass
class AgentContext:
    """
    Shared context for all agent tools.

    This context is passed to every tool via the RunContextWrapper's context dict.
    It provides centralized access to storage, state, API credentials, and logging.

    Attributes:
        storage: GlossStorage instance for database operations
        state: Dict containing situation_ref, native_language, target_language
        api_key: OpenAI API key for LLM calls
        logger: Logger instance for structured logging

    Example:
        >>> from agent.context import AgentContext
        >>> from agent.logging_config import setup_agent_logging
        >>>
        >>> ctx = AgentContext(
        ...     storage=GlossStorage(data_root=Path("data")),
        ...     state={
        ...         "situation_ref": "eng:cooking-together",
        ...         "native_language": "eng",
        ...         "target_language": "deu",
        ...     },
        ...     api_key=os.getenv("OPENAI_API_KEY"),
        ...     logger=setup_agent_logging(),
        ... )
    """

    storage: GlossStorage
    state: dict[str, Any]
    api_key: str
    logger: logging.Logger

    @property
    def native_language(self) -> str:
        """Get native language code from state."""
        return self.state["native_language"]

    @property
    def target_language(self) -> str:
        """Get target language code from state."""
        return self.state["target_language"]

    @property
    def situation_ref(self) -> str:
        """Get situation reference from state."""
        return self.state["situation_ref"]

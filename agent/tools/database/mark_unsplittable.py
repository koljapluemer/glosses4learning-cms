"""Tool for marking glosses as unsplittable."""

from __future__ import annotations

from typing import Annotated

from agents.run_context import RunContextWrapper
from agents.tool import function_tool

from agent.logging_config import LogContext
from src.shared.gloss_operations import mark_gloss_log
from src.shared.tree import SPLIT_LOG_MARKER

def mark_unsplittable(
    ctx: RunContextWrapper,
    gloss_ref: Annotated[str, "Reference to gloss (format: 'lang:slug')"],
) -> str:
    """
    Mark a gloss as not splittable into parts.

    This is used for glosses that cannot be meaningfully broken down into
    constituent parts (e.g., single words, particles, atomic expressions).

    Adds the log marker "SPLIT_CONSIDERED_UNNECESSARY" to prevent the agent
    from repeatedly trying to split this gloss.

    Args:
        gloss_ref: Reference to the gloss to mark

    Returns:
        Success message or error message

    Example:
        mark_unsplittable(ctx, "spa:bien")
        -> "Successfully marked spa:bien as unsplittable"
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger

    with LogContext(logger, tool="mark_unsplittable", gloss_ref=gloss_ref):
        logger.info(f"Marking {gloss_ref} as unsplittable")

        try:
            mark_gloss_log(storage, gloss_ref, SPLIT_LOG_MARKER)
            logger.info(f"Successfully marked {gloss_ref} as unsplittable")
            return f"Successfully marked {gloss_ref} as unsplittable (SPLIT_CONSIDERED_UNNECESSARY)"

        except Exception as e:
            error_msg = f"Failed to mark unsplittable: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

mark_unsplittable_tool = function_tool(mark_unsplittable)

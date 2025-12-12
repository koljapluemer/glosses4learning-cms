"""Tool for marking glosses where usage examples are not appropriate."""

from __future__ import annotations

from typing import Annotated

from agents import RunContextWrapper, function_tool

from agent.logging_config import LogContext
from src.shared.gloss_operations import mark_gloss_log

@function_tool
def mark_no_usage_examples(
    ctx: RunContextWrapper,
    gloss_ref: Annotated[str, "Reference to gloss (format: 'lang:slug')"],
    target_language: Annotated[str, "Language code for which examples are impossible"],
) -> str:
    """
    Mark a gloss as not needing usage examples in a specific language.

    This is used for glosses that are complete sentences themselves, or where
    usage examples would not make sense (e.g., a sentence that is already an example).

    Adds the log marker "USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE:{language}" to prevent
    the agent from repeatedly trying to generate examples.

    Args:
        gloss_ref: Reference to the gloss to mark
        target_language: ISO 639-3 code of language for which examples are not needed

    Returns:
        Success message or error message

    Example:
        mark_no_usage_examples(ctx, "arb:الرحلة ستتأخر", "arb")
        -> "Successfully marked arb:الرحلة ستتأخر as not needing usage examples"
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger

    with LogContext(logger, tool="mark_no_usage_examples", gloss_ref=gloss_ref):
        logger.info(f"Marking {gloss_ref} as not needing usage examples in {target_language}")

        try:
            target_language = target_language.lower().strip()
            marker = f"USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE:{target_language}"

            mark_gloss_log(storage, gloss_ref, marker)
            logger.info(f"Successfully marked {gloss_ref}")
            return f"Successfully marked {gloss_ref} as not needing usage examples in {target_language}"

        except Exception as e:
            error_msg = f"Failed to mark no usage examples: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

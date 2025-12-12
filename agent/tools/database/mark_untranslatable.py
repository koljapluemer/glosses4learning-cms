"""Tool for marking glosses as untranslatable to a specific language."""

from __future__ import annotations

from typing import Annotated

from agents.run_context import RunContextWrapper
from agents.tool import function_tool

from agent.logging_config import LogContext
from src.shared.gloss_operations import mark_gloss_log

def mark_untranslatable(
    ctx: RunContextWrapper,
    gloss_ref: Annotated[str, "Reference to gloss (format: 'lang:slug')"],
    target_language: Annotated[str, "Language code that translation is impossible to"],
) -> str:
    """
    Mark a gloss as untranslatable to a specific language.

    This is used for glosses that don't have meaningful translations in the
    target language (e.g., language-specific punctuation, proper nouns, etc.).

    Adds the log marker "TRANSLATION_CONSIDERED_IMPOSSIBLE:{language}" to prevent
    the agent from repeatedly trying to translate this gloss.

    Args:
        gloss_ref: Reference to the gloss to mark
        target_language: ISO 639-3 code of language that translation is impossible to

    Returns:
        Success message or error message

    Example:
        mark_untranslatable(ctx, "arb:؟", "eng")
        -> "Successfully marked arb:؟ as untranslatable to eng"
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger

    with LogContext(logger, tool="mark_untranslatable", gloss_ref=gloss_ref):
        logger.info(f"Marking {gloss_ref} as untranslatable to {target_language}")

        try:
            target_language = target_language.lower().strip()
            marker = f"TRANSLATION_CONSIDERED_IMPOSSIBLE:{target_language}"

            mark_gloss_log(storage, gloss_ref, marker)
            logger.info(f"Successfully marked {gloss_ref} as untranslatable to {target_language}")
            return f"Successfully marked {gloss_ref} as untranslatable to {target_language}"

        except Exception as e:
            error_msg = f"Failed to mark untranslatable: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

mark_untranslatable_tool = function_tool(mark_untranslatable)

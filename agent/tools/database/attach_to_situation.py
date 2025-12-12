"""Tool for attaching existing glosses to a situation."""

from __future__ import annotations

from typing import Annotated

from agents.run_context import RunContextWrapper
from agents.tool import function_tool

from agent.logging_config import LogContext
from src.shared.storage import attach_relation

def attach_to_situation(
    ctx: RunContextWrapper,
    gloss_ref: Annotated[str, "Reference to gloss to attach (format: 'lang:slug')"],
    situation_ref: Annotated[str, "Situation reference (format: 'lang:slug')"],
) -> str:
    """
    Attach an existing gloss to a situation as a child.

    This is useful for adding existing goals or glosses to a situation
    without recreating them. The gloss must already exist in storage.

    Args:
        gloss_ref: Reference to the gloss to attach
        situation_ref: Reference to the situation

    Returns:
        Success message or error message

    Example:
        attach_to_situation(ctx, "eng:ask for help", "eng:at-the-airport")
        -> "Successfully attached eng:ask for help to situation eng:at-the-airport"
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger

    with LogContext(logger, tool="attach_to_situation", gloss_ref=gloss_ref, situation_ref=situation_ref):
        logger.info(f"Attaching {gloss_ref} to situation {situation_ref}")

        try:
            # Load situation
            situation = storage.resolve_reference(situation_ref)
            if not situation:
                return f"Error: Situation not found: {situation_ref}"

            # Load gloss
            gloss = storage.resolve_reference(gloss_ref)
            if not gloss:
                return f"Error: Gloss not found: {gloss_ref}"

            # Attach to situation
            attach_relation(storage, situation, "children", gloss)

            logger.info(f"Successfully attached {gloss_ref} to {situation_ref}")
            return f"Successfully attached {gloss_ref} to situation {situation_ref}"

        except Exception as e:
            error_msg = f"Failed to attach to situation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

attach_to_situation_tool = function_tool(attach_to_situation)

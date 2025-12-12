"""Tool for adding parts to a gloss."""

from __future__ import annotations

from typing import Annotated

from agents.run_context import RunContextWrapper
from agents.tool import function_tool

from agent.logging_config import LogContext
from src.shared.storage import attach_relation

def add_parts(
    ctx: RunContextWrapper,
    gloss_ref: Annotated[str, "Reference to gloss to add parts to (format: 'lang:slug')"],
    part_refs: Annotated[list[str], "List of part references (format: ['lang:slug', ...])"],
) -> str:
    """
    Add parts (components) to a gloss.

    Parts are constituent elements that make up the gloss. For example,
    "I run away" might have parts ["eng:I", "eng:run", "eng:away"].

    All parts must be in the same language as the parent gloss.

    Args:
        gloss_ref: Reference to the parent gloss
        part_refs: List of references to the part glosses

    Returns:
        Success message with added parts count, or error message

    Example:
        add_parts(ctx, "eng:I run away", ["eng:I", "eng:run", "eng:away"])
        -> "Successfully added 3 parts to eng:I run away"
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger

    with LogContext(logger, tool="add_parts", gloss_ref=gloss_ref):
        logger.info(f"Adding {len(part_refs)} parts to {gloss_ref}")

        try:
            # Load parent gloss
            gloss = storage.resolve_reference(gloss_ref)
            if not gloss:
                error_msg = f"Gloss not found: {gloss_ref}"
                logger.error(error_msg)
                return f"Error: {error_msg}"

            # Validate and add parts
            added_count = 0
            errors = []

            for part_ref in part_refs:
                try:
                    # Load part gloss to validate it exists
                    part_gloss = storage.resolve_reference(part_ref)
                    if not part_gloss:
                        errors.append(f"Part not found: {part_ref}")
                        continue

                    # Verify same language (within-language relationship)
                    if part_gloss.language != gloss.language:
                        errors.append(f"Part {part_ref} has different language than parent {gloss_ref}")
                        continue

                    # Attach part
                    attach_relation(storage, gloss, "parts", part_gloss)
                    added_count += 1
                    logger.info(f"Added part: {part_ref}")

                except Exception as e:
                    errors.append(f"Failed to add part {part_ref}: {str(e)}")

            # Prepare response
            if errors:
                error_summary = "; ".join(errors)
                logger.warning(f"Added {added_count} parts with {len(errors)} errors: {error_summary}")
                return f"Added {added_count} parts to {gloss_ref}. Errors: {error_summary}"
            else:
                logger.info(f"Successfully added {added_count} parts")
                return f"Successfully added {added_count} parts to {gloss_ref}"

        except Exception as e:
            error_msg = f"Failed to add parts: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

add_parts_tool = function_tool(add_parts)

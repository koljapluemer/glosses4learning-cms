"""Tool for adding usage examples to a gloss."""

from __future__ import annotations

from typing import Annotated

from agents.run_context import RunContextWrapper
from agents.tool import function_tool

from agent.logging_config import LogContext
from src.shared.storage import attach_relation

def add_usage_examples(
    ctx: RunContextWrapper,
    gloss_ref: Annotated[str, "Reference to gloss to add examples to (format: 'lang:slug')"],
    example_refs: Annotated[list[str], "List of example sentence references"],
) -> str:
    """
    Add usage example sentences to a gloss.

    Usage examples are sentences that demonstrate how the gloss is used in context.
    The gloss should appear in the example sentence's parts array.

    All examples must be in the same language as the gloss.

    Args:
        gloss_ref: Reference to the gloss
        example_refs: List of references to example sentence glosses

    Returns:
        Success message with count, or error message

    Example:
        add_usage_examples(ctx, "eng:tree", ["eng:The tree is green"])
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger

    with LogContext(logger, tool="add_usage_examples", gloss_ref=gloss_ref):
        logger.info(f"Adding {len(example_refs)} usage examples to {gloss_ref}")

        try:
            gloss = storage.resolve_reference(gloss_ref)
            if not gloss:
                return f"Error: Gloss not found: {gloss_ref}"

            added_count = 0
            errors = []

            for example_ref in example_refs:
                try:
                    example_gloss = storage.resolve_reference(example_ref)
                    if not example_gloss:
                        errors.append(f"Example not found: {example_ref}")
                        continue

                    if example_gloss.language != gloss.language:
                        errors.append(f"Example {example_ref} has different language")
                        continue

                    attach_relation(storage, gloss, "usage_examples", example_gloss)
                    added_count += 1

                except Exception as e:
                    errors.append(f"Failed to add {example_ref}: {str(e)}")

            if errors:
                error_summary = "; ".join(errors)
                logger.warning(f"Added {added_count} examples with errors")
                return f"Added {added_count} examples to {gloss_ref}. Errors: {error_summary}"
            else:
                logger.info(f"Successfully added {added_count} examples")
                return f"Successfully added {added_count} usage examples to {gloss_ref}"

        except Exception as e:
            error_msg = f"Failed to add usage examples: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

add_usage_examples_tool = function_tool(add_usage_examples)

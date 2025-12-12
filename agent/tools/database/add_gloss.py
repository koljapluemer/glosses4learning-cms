"""Tool for adding glosses to storage."""

from __future__ import annotations

from typing import Annotated

from agents.run_context import RunContextWrapper
from agents.tool import function_tool

from agent.logging_config import LogContext
from src.shared.storage import Gloss


def add_gloss(
    ctx: RunContextWrapper,
    content: Annotated[str, "The gloss content/text to add"],
    language: Annotated[str, "ISO 639-3 language code (e.g., 'eng', 'deu', 'arb')"],
    tags: Annotated[list[str] | None, "Optional list of tag references to add"] = None,
) -> str:
    """
    Add a gloss to storage or return existing gloss.

    If a gloss with this content already exists in the language, returns
    the existing gloss reference. Otherwise creates a new one.

    The gloss content should be the actual text (word, phrase, or sentence)
    in the specified language. Tags can be added to categorize the gloss.

    Args:
        content: The text content of the gloss
        language: Three-letter ISO 639-3 language code
        tags: Optional list of tag references (format: "lang:slug")

    Returns:
        Success message with gloss reference, or error message

    Example:
        add_gloss(ctx, "Hello", "eng", ["eng:greeting"])
        -> "Successfully added/found gloss 'Hello'. Reference: eng:Hello"
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger

    with LogContext(logger, tool="add_gloss"):
        logger.info(f"Adding gloss: '{content}' in language '{language}'")

        try:
            # Normalize language code
            language = language.lower().strip()

            # Check if gloss already exists
            existing = storage.find_gloss_by_content(language, content)

            if existing:
                # Update tags if provided and not already present
                if tags:
                    current_tags = existing.tags or []
                    new_tags = []
                    for tag in tags:
                        if tag not in current_tags:
                            current_tags.append(tag)
                            new_tags.append(tag)

                    if new_tags:
                        existing.tags = current_tags
                        storage.save_gloss(existing)
                        logger.info(f"Updated existing gloss with tags: {new_tags}")

                gloss_ref = f"{existing.language}:{existing.slug}"
                logger.info(f"Gloss already exists: {gloss_ref}")
                return f"Gloss already exists: '{content}'. Reference: {gloss_ref}. Tags: {existing.tags or []}"

            # Create new gloss
            gloss = Gloss(
                content=content,
                language=language,
                tags=tags or [],
            )

            created = storage.create_gloss(gloss)
            gloss_ref = f"{created.language}:{created.slug}"

            logger.info(f"Created new gloss: {gloss_ref}")
            return f"Successfully created gloss '{content}'. Reference: {gloss_ref}. Tags: {created.tags or []}"

        except Exception as e:
            error_msg = f"Failed to add gloss '{content}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

add_gloss_tool = function_tool(add_gloss)

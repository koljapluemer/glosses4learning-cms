"""Tool for adding notes to glosses."""

from __future__ import annotations

from typing import Annotated

from agents.run_context import RunContextWrapper
from agents.tool import function_tool

from agent.logging_config import LogContext
from src.shared.storage import attach_relation

def add_note(
    ctx: RunContextWrapper,
    gloss_ref: Annotated[str, "Reference to gloss to add note to (format: 'lang:slug')"],
    note_text: Annotated[str, "Note text content"],
    note_language: Annotated[str, "ISO 639-3 code for note language"],
) -> str:
    """
    Add a note gloss to another gloss.

    Notes are typically used to provide usage guidance, context, or explanations.
    The relationship is one-way (gloss -> note), not bidirectional.

    Notes can be in any language (often the native language for learners).

    Args:
        gloss_ref: Reference to the gloss to annotate
        note_text: Content of the note
        note_language: Language code for the note

    Returns:
        Success message with note reference, or error message

    Example:
        add_note(ctx, "deu:Tschüss", "informal", "eng")
        -> "Successfully added note 'informal' to deu:Tschüss. Reference: eng:informal"
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger

    with LogContext(logger, tool="add_note", gloss_ref=gloss_ref):
        logger.info(f"Adding note '{note_text}' to {gloss_ref}")

        try:
            # Load target gloss
            gloss = storage.resolve_reference(gloss_ref)
            if not gloss:
                return f"Error: Gloss not found: {gloss_ref}"

            # Create or find note gloss
            note_language = note_language.lower().strip()
            note_gloss = storage.ensure_gloss(note_language, note_text.strip())
            note_ref = f"{note_gloss.language}:{note_gloss.slug}"

            # Attach note (one-way relationship)
            attach_relation(storage, gloss, "notes", note_gloss)

            logger.info(f"Successfully added note: {note_ref}")
            return f"Successfully added note '{note_text}' to {gloss_ref}. Reference: {note_ref}"

        except Exception as e:
            error_msg = f"Failed to add note: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

add_note_tool = function_tool(add_note)

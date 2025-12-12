"""Tool for adding translations between glosses."""

from __future__ import annotations

from typing import Annotated

from agents import RunContextWrapper, function_tool

from agent.logging_config import LogContext
from src.shared.gloss_operations import attach_translation_with_note

@function_tool
def add_translation(
    ctx: RunContextWrapper,
    source_gloss_ref: Annotated[str, "Source gloss reference (format: 'lang:slug')"],
    translation_text: Annotated[str, "Translation text in target language"],
    translation_language: Annotated[str, "ISO 639-3 code for translation language"],
    note_text: Annotated[str | None, "Optional usage note in native language"] = None,
    note_language: Annotated[str | None, "Language code for note (usually native language)"] = None,
) -> str:
    """
    Add a translation to a gloss with optional usage note.

    Creates a bidirectional translation relationship between the source gloss
    and a translation gloss. If the translation gloss doesn't exist, it will be created.
    Optionally attaches a one-way note to the translation to explain its usage.

    Args:
        source_gloss_ref: Reference to the source gloss (e.g., "eng:hello")
        translation_text: The translation text
        translation_language: Language code for the translation
        note_text: Optional note explaining when/how to use this translation
        note_language: Language code for the note (required if note_text provided)

    Returns:
        Success message with translation reference, or error message

    Example:
        add_translation(ctx, "eng:express gratitude", "Danke", "deu", "informal", "eng")
        -> "Successfully added translation 'Danke' to eng:express gratitude. Reference: deu:Danke"
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger

    with LogContext(logger, tool="add_translation", gloss_ref=source_gloss_ref):
        logger.info(f"Adding translation '{translation_text}' ({translation_language}) to {source_gloss_ref}")

        try:
            # Load source gloss
            source_gloss = storage.resolve_reference(source_gloss_ref)
            if not source_gloss:
                error_msg = f"Source gloss not found: {source_gloss_ref}"
                logger.error(error_msg)
                return f"Error: {error_msg}"

            # Validate note parameters
            if note_text and not note_language:
                error_msg = "note_language required when note_text is provided"
                logger.error(error_msg)
                return f"Error: {error_msg}"

            # Normalize language codes
            translation_language = translation_language.lower().strip()
            if note_language:
                note_language = note_language.lower().strip()

            # Attach translation with optional note
            translation_gloss = attach_translation_with_note(
                storage=storage,
                source_gloss=source_gloss,
                translation_text=translation_text,
                translation_language=translation_language,
                note_text=note_text,
                note_language=note_language or agent_ctx.native_language,
            )

            translation_ref = f"{translation_gloss.language}:{translation_gloss.slug}"
            logger.info(f"Successfully added translation: {translation_ref}")

            note_msg = f" with note '{note_text}'" if note_text else ""
            return f"Successfully added translation '{translation_text}' to {source_gloss_ref}. Reference: {translation_ref}{note_msg}"

        except Exception as e:
            error_msg = f"Failed to add translation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

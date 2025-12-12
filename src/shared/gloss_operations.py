"""Common gloss manipulation operations extracted from flows."""

from __future__ import annotations

from datetime import datetime

from src.shared.storage import Gloss, GlossStorage, attach_relation


def attach_translation_with_note(
    storage: GlossStorage,
    source_gloss: Gloss,
    translation_text: str,
    translation_language: str,
    note_text: str | None,
    note_language: str,
) -> Gloss:
    """
    Attach translation to gloss with optional note.

    Creates a bidirectional translation relationship and optionally
    attaches a one-way note to the translation gloss.

    Extracted from src/tui/flows/flow_translate_paraphrases_to_target_ai.py
    to avoid code duplication across flows and agent tools.

    Args:
        storage: GlossStorage instance
        source_gloss: Source gloss to translate from
        translation_text: Translation text in target language
        translation_language: Target language code
        note_text: Optional note text in native language
        note_language: Language code for the note (typically native language)

    Returns:
        The created/found translation gloss

    Example:
        >>> storage = GlossStorage(data_root=Path("data"))
        >>> native_gloss = storage.find_gloss_by_content("eng", "express gratitude")
        >>> translation = attach_translation_with_note(
        ...     storage, native_gloss, "Danke", "deu",
        ...     "informal", "eng"
        ... )
    """
    # Create or find translation gloss
    translation_gloss = storage.ensure_gloss(translation_language, translation_text)

    # Bidirectional translation relation
    attach_relation(storage, source_gloss, "translations", translation_gloss)
    attach_relation(storage, translation_gloss, "translations", source_gloss)

    # One-way note relation (if note exists)
    # Note is in native language, attached TO the target translation
    if note_text and note_text.strip():
        note_gloss = storage.ensure_gloss(note_language, note_text.strip())
        attach_relation(storage, translation_gloss, "notes", note_gloss)

    return translation_gloss


def mark_gloss_log(
    storage: GlossStorage,
    gloss_ref: str,
    marker: str,
) -> None:
    """
    Add a log marker to a gloss.

    Used for marking glosses with special states like:
    - SPLIT_CONSIDERED_UNNECESSARY
    - TRANSLATION_CONSIDERED_IMPOSSIBLE:{language}
    - USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE:{language}

    The log entry is timestamped with UTC ISO format to track when
    the decision was made. This prevents the agent from repeatedly
    attempting impossible operations.

    Args:
        storage: GlossStorage instance
        gloss_ref: Gloss reference in format "language:slug"
        marker: Log marker string to add

    Raises:
        ValueError: If gloss not found

    Example:
        >>> mark_gloss_log(storage, "arb:؟", "TRANSLATION_CONSIDERED_IMPOSSIBLE:eng")
        >>> mark_gloss_log(storage, "spa:sal", "SPLIT_CONSIDERED_UNNECESSARY")
    """
    gloss = storage.resolve_reference(gloss_ref)
    if not gloss:
        raise ValueError(f"Gloss not found: {gloss_ref}")

    # Ensure logs is a dict, not None or other type
    logs = gloss.logs if isinstance(getattr(gloss, "logs", {}), dict) else {}

    # Add timestamped marker
    timestamp = datetime.utcnow().isoformat() + "Z"
    logs[timestamp] = marker

    # Save updated gloss
    gloss.logs = logs
    storage.save_gloss(gloss)

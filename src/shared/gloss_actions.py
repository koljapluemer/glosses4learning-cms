"""Single-gloss action wrappers for UI operations.

This module provides reusable functions for common gloss operations
that can be called from both the tk UI and Flask apps without requiring
the agent framework context.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.shared.storage import GlossStorage, RELATIONSHIP_FIELDS, attach_relation
from src.shared.gloss_operations import attach_translation_with_note
from src.shared.languages import get_ai_note
from src.shared.llm_client import get_openai_client


def delete_gloss_with_cleanup(
    storage: GlossStorage,
    language: str,
    slug: str,
) -> tuple[bool, str]:
    """
    Delete gloss and clean all references.

    Extracted from Flask delete_gloss to provide reusable deletion logic.

    Args:
        storage: GlossStorage instance
        language: Language code of gloss to delete
        slug: Slug of gloss to delete

    Returns:
        (success: bool, message: str)
    """
    try:
        # Load gloss to verify it exists
        gloss = storage.load_gloss(language, slug)
        if not gloss:
            return False, f"Gloss not found: {language}:{slug}"

        # Delete the file
        target = storage._path_for(language, slug)  # type: ignore[attr-defined]
        target.unlink(missing_ok=True)  # type: ignore[attr-defined]

        # Scan all glosses and remove references
        removed_refs = 0
        gloss_ref = f"{language}:{slug}"

        for item in storage.list_glosses():
            changed = False
            for field in RELATIONSHIP_FIELDS:
                refs: list[str] = list(getattr(item, field, []) or [])
                filtered = [ref for ref in refs if ref != gloss_ref]
                if len(filtered) != len(refs):
                    setattr(item, field, filtered)
                    changed = True
            if changed:
                removed_refs += 1
                storage.save_gloss(item)

        return True, f"Deleted {gloss_ref}. Cleaned references in {removed_refs} glosses."

    except Exception as e:
        return False, f"Failed to delete gloss: {str(e)}"


def set_needs_human_check(
    storage: GlossStorage,
    gloss_ref: str,
    value: bool = True,
) -> tuple[bool, str]:
    """
    Set needsHumanCheck flag on gloss.

    Args:
        storage: GlossStorage instance
        gloss_ref: Gloss reference (format: "language:slug")
        value: Flag value to set (default: True)

    Returns:
        (success: bool, message: str)
    """
    try:
        gloss = storage.resolve_reference(gloss_ref)
        if not gloss:
            return False, f"Gloss not found: {gloss_ref}"

        gloss.needsHumanCheck = value
        storage.save_gloss(gloss)

        status = "set" if value else "unset"
        return True, f"needsHumanCheck {status} for {gloss_ref}"

    except Exception as e:
        return False, f"Failed to update flag: {str(e)}"


def set_exclude_from_learning(
    storage: GlossStorage,
    gloss_ref: str,
    value: bool = True,
) -> tuple[bool, str]:
    """
    Set excludeFromLearning flag on gloss.

    Args:
        storage: GlossStorage instance
        gloss_ref: Gloss reference (format: "language:slug")
        value: Flag value to set (default: True)

    Returns:
        (success: bool, message: str)
    """
    try:
        gloss = storage.resolve_reference(gloss_ref)
        if not gloss:
            return False, f"Gloss not found: {gloss_ref}"

        gloss.excludeFromLearning = value
        storage.save_gloss(gloss)

        status = "set" if value else "unset"
        return True, f"excludeFromLearning {status} for {gloss_ref}"

    except Exception as e:
        return False, f"Failed to update flag: {str(e)}"


def generate_translations_for_gloss(
    storage: GlossStorage,
    gloss_ref: str,
    target_language: str,
    native_language: str,
    api_key: str,
) -> tuple[list[dict], list[str]]:
    """
    Generate translations for a single gloss (skip usefulness check).

    Args:
        storage: GlossStorage instance
        gloss_ref: Gloss reference to translate
        target_language: Target language code
        native_language: Native language code
        api_key: OpenAI API key

    Returns:
        (translations: list[dict], errors: list[str])
        Each translation: {"text": str, "note": str, "ref": str}
    """
    errors = []
    translations = []

    try:
        # Load gloss
        gloss = storage.resolve_reference(gloss_ref)
        if not gloss:
            errors.append(f"Gloss not found: {gloss_ref}")
            return translations, errors

        # Determine translation direction
        if gloss.language == native_language:
            # Native to target
            to_language = target_language
        elif gloss.language == target_language:
            # Target to native
            to_language = native_language
        else:
            errors.append(f"Gloss language {gloss.language} is neither native nor target")
            return translations, errors

        # Get language AI note
        ai_note = get_ai_note(to_language)
        ai_note_text = f"Language notes: {ai_note}" if ai_note else ""

        # Build prompt
        prompt = f"""Translate "{gloss.content}" from {gloss.language} to {to_language}.

Provide 2-4 natural translations that a native speaker would use.
Include usage notes ONLY when there are important distinctions (formality, context, etc.).

{ai_note_text}

Return JSON with translations array. Each item:
- "text": the translation (REQUIRED)
- "note": usage note in {native_language}; use an empty string if not needed (REQUIRED)"""

        # Call LLM
        client = get_openai_client(api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional translator providing accurate translations between languages."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=500,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "translation_list",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "translations": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "text": {"type": "string"},
                                        "note": {"type": "string"},
                                    },
                                    "required": ["text", "note"],
                                    "additionalProperties": False,
                                },
                            }
                        },
                        "required": ["translations"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                },
            },
        )

        content = response.choices[0].message.content.strip()
        data = json.loads(content)
        translation_items = data.get("translations", [])

        # Persist translations
        for item in translation_items:
            text = item.get("text", "").strip()
            note = item.get("note", "").strip()

            if not text:
                continue

            try:
                # Create translation with optional note
                translation_gloss = attach_translation_with_note(
                    storage=storage,
                    source_gloss=gloss,
                    translation_text=text,
                    translation_language=to_language,
                    note_text=note if note else None,
                    note_language=native_language,
                )

                translation_ref = f"{translation_gloss.language}:{translation_gloss.slug}"
                translations.append({
                    "text": text,
                    "note": note,
                    "ref": translation_ref,
                })

            except Exception as e:
                errors.append(f"Failed to persist translation '{text}': {str(e)}")

        return translations, errors

    except Exception as e:
        errors.append(f"Failed to generate translations: {str(e)}")
        return translations, errors


def generate_parts_for_gloss(
    storage: GlossStorage,
    gloss_ref: str,
    api_key: str,
) -> tuple[list[str], list[str]]:
    """
    Generate parts for a single gloss (skip splittability check).

    Args:
        storage: GlossStorage instance
        gloss_ref: Gloss reference to split
        api_key: OpenAI API key

    Returns:
        (parts: list[str], errors: list[str])
        Parts are gloss references
    """
    errors = []
    parts = []

    try:
        # Load gloss
        gloss = storage.resolve_reference(gloss_ref)
        if not gloss:
            errors.append(f"Gloss not found: {gloss_ref}")
            return parts, errors

        # Get language AI note
        ai_note = get_ai_note(gloss.language)
        ai_note_text = f"Language notes: {ai_note}" if ai_note else ""

        # Build prompt
        prompt = f"""Take this {gloss.language} expression or phrase and break it up into parts that can be learned on their own.

Expression: {gloss.content}

Return a JSON object with a 'parts' array of strings. Avoid repetition.

{ai_note_text}"""

        # Call LLM
        client = get_openai_client(api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a concise linguistic decomposition assistant.\n\nBreak expressions into learnable component parts - words or meaningful sub-expressions."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=200,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "parts_list",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "parts": {
                                "type": "array",
                                "items": {"type": "string"},
                            }
                        },
                        "required": ["parts"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                },
            },
        )

        content = response.choices[0].message.content.strip()
        data = json.loads(content)
        part_texts = data.get("parts", [])

        # Clean and filter parts
        part_texts = [p.strip() for p in part_texts if isinstance(p, str) and p.strip()]

        if not part_texts:
            return parts, errors

        # Persist parts
        for part_text in part_texts:
            try:
                # Ensure part gloss exists
                part_gloss = storage.ensure_gloss(gloss.language, part_text)
                part_ref = f"{part_gloss.language}:{part_gloss.slug}"

                # Attach part relation
                attach_relation(storage, gloss, "parts", part_gloss)
                parts.append(part_ref)

            except Exception as e:
                errors.append(f"Failed to persist part '{part_text}': {str(e)}")

        return parts, errors

    except Exception as e:
        errors.append(f"Failed to generate parts: {str(e)}")
        return parts, errors


def generate_usage_examples_for_gloss(
    storage: GlossStorage,
    gloss_ref: str,
    api_key: str,
    num_examples: int = 3,
) -> tuple[list[str], list[str]]:
    """
    Generate usage examples for a single gloss (skip usefulness check).

    Args:
        storage: GlossStorage instance
        gloss_ref: Gloss reference to create examples for
        api_key: OpenAI API key
        num_examples: Number of examples to generate (default: 3)

    Returns:
        (examples: list[str], errors: list[str])
        Examples are gloss references
    """
    errors = []
    examples = []

    try:
        # Load gloss
        gloss = storage.resolve_reference(gloss_ref)
        if not gloss:
            errors.append(f"Gloss not found: {gloss_ref}")
            return examples, errors

        # Get language AI note
        ai_note = get_ai_note(gloss.language)
        ai_note_text = f"Language notes: {ai_note}" if ai_note else ""

        # Build prompt
        prompt = f"""Generate {num_examples} example sentences that use the {gloss.language} word/phrase: "{gloss.content}"

The gloss should appear naturally in each sentence. Keep sentences practical and relevant for learners.

{ai_note_text}

Return JSON with an "examples" array of sentence strings."""

        # Call LLM
        client = get_openai_client(api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You generate concise usage example sentences for language learning.\n\nCreate natural, practical sentences that demonstrate how the word or phrase is used in context."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=400,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "example_list",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "examples": {
                                "type": "array",
                                "items": {"type": "string"},
                            }
                        },
                        "required": ["examples"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                },
            },
        )

        content = response.choices[0].message.content.strip()
        data = json.loads(content)
        example_texts = data.get("examples", [])

        # Clean and filter examples
        example_texts = [e.strip() for e in example_texts if isinstance(e, str) and e.strip()]

        if not example_texts:
            return examples, errors

        # Persist examples
        for example_text in example_texts:
            try:
                # Ensure example gloss exists
                example_gloss = storage.ensure_gloss(gloss.language, example_text)
                example_ref = f"{example_gloss.language}:{example_gloss.slug}"

                # Attach usage_examples relation
                attach_relation(storage, gloss, "usage_examples", example_gloss)
                examples.append(example_ref)

            except Exception as e:
                errors.append(f"Failed to persist example '{example_text}': {str(e)}")

        return examples, errors

    except Exception as e:
        errors.append(f"Failed to generate examples: {str(e)}")
        return examples, errors

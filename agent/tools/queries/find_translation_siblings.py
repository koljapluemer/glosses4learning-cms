"""Tool for finding translation siblings that need usage notes."""

from __future__ import annotations

import json
from typing import Annotated

from agents import RunContextWrapper, function_tool

from agent.logging_config import LogContext
from src.shared.tree import collect_situation_stats

@function_tool
def find_translation_siblings(
    ctx: RunContextWrapper,
    situation_ref: Annotated[str | None, "Situation reference. If None, uses current situation."] = None,
) -> str:
    """
    Find translation siblings that need usage notes.

    Translation siblings are multiple translations of the same source gloss.
    When a native gloss has 2+ translations into the target language, they
    should have notes explaining when/how to use each one.

    This tool identifies native glosses that have multiple target translations
    but where those translations don't have notes attached.

    Args:
        situation_ref: Situation reference (uses context if None)

    Returns:
        JSON string with groups of translation siblings

    Example Output:
        {
            "count": 2,
            "sibling_groups": [
                {
                    "native_ref": "eng:express gratitude",
                    "native_content": "express gratitude",
                    "translations": [
                        {"ref": "deu:Danke", "content": "Danke", "has_note": false},
                        {"ref": "deu:Dankeschön", "content": "Dankeschön", "has_note": false}
                    ]
                },
                ...
            ]
        }
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger
    native_language = agent_ctx.native_language
    target_language = agent_ctx.target_language

    if situation_ref is None:
        situation_ref = agent_ctx.situation_ref

    with LogContext(logger, tool="find_translation_siblings", situation_ref=situation_ref):
        logger.info(f"Finding translation siblings for {situation_ref}")

        try:
            situation = storage.resolve_reference(situation_ref)
            if not situation:
                return json.dumps({"error": f"Situation not found: {situation_ref}"})

            stats = collect_situation_stats(storage, situation, native_language, target_language)
            all_glosses = stats.get("situation_glosses", [])

            sibling_groups = []

            # Check each native language gloss
            for ref in all_glosses:
                gloss = storage.resolve_reference(ref)
                if not gloss or gloss.language != native_language:
                    continue

                # Find target language translations
                target_translations = []
                for trans_ref in (gloss.translations or []):
                    trans_gloss = storage.resolve_reference(trans_ref)
                    if trans_gloss and trans_gloss.language == target_language:
                        # Check if it has notes
                        has_note = bool(trans_gloss.notes and len(trans_gloss.notes) > 0)
                        target_translations.append({
                            "ref": trans_ref,
                            "content": trans_gloss.content,
                            "has_note": has_note,
                        })

                # If 2+ translations and any lack notes, add to results
                if len(target_translations) >= 2:
                    needs_notes = any(not t["has_note"] for t in target_translations)
                    if needs_notes:
                        sibling_groups.append({
                            "native_ref": ref,
                            "native_content": gloss.content,
                            "translations": target_translations,
                        })

            result = {
                "count": len(sibling_groups),
                "sibling_groups": sibling_groups,
            }

            logger.info(f"Found {len(sibling_groups)} sibling groups needing notes")
            return json.dumps(result, indent=2, ensure_ascii=False)

        except Exception as e:
            error_msg = f"Failed to find translation siblings: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return json.dumps({"error": error_msg})

"""Tool for listing glosses with missing translations."""

from __future__ import annotations

import json
from typing import Annotated

from agents.run_context import RunContextWrapper
from agents.tool import function_tool

from agent.logging_config import LogContext
from src.shared.tree import collect_situation_stats

def list_missing_translations(
    ctx: RunContextWrapper,
    situation_ref: Annotated[str | None, "Situation reference. If None, uses current situation."] = None,
    category: Annotated[str, "Category: 'native', 'target', 'paraphrased_native', or 'all'"] = "all",
) -> str:
    """
    List glosses that are missing translations.

    Returns glosses categorized by type:
    - native: Native language glosses missing target translations
    - target: Target language glosses missing native translations
    - paraphrased_native: Native paraphrases missing target translations

    Args:
        situation_ref: Situation reference (uses context if None)
        category: Which category to return ('all' for all categories)

    Returns:
        JSON string with missing translation references by category

    Example Output:
        {
            "native_missing": ["eng:hello", "eng:goodbye"],
            "target_missing": ["deu:Hallo", "deu:Tschüss"],
            "paraphrased_native_missing": ["eng:express gratitude"]
        }
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger
    native_language = agent_ctx.native_language
    target_language = agent_ctx.target_language

    if situation_ref is None:
        situation_ref = agent_ctx.situation_ref

    with LogContext(logger, tool="list_missing_translations", situation_ref=situation_ref):
        logger.info(f"Listing missing translations for {situation_ref}, category: {category}")

        try:
            situation = storage.resolve_reference(situation_ref)
            if not situation:
                return json.dumps({"error": f"Situation not found: {situation_ref}"})

            stats = collect_situation_stats(storage, situation, native_language, target_language)

            # Categorize missing translations
            native_missing = []
            target_missing = []
            paraphrased_native_missing = []

            for ref in stats.get("native_missing", []):
                gloss = storage.resolve_reference(ref)
                if gloss and "eng:paraphrase" in (gloss.tags or []):
                    paraphrased_native_missing.append(ref)
                else:
                    native_missing.append(ref)

            target_missing = list(stats.get("target_missing", []))

            # Build result based on category
            if category == "native":
                result = {"native_missing": native_missing, "count": len(native_missing)}
            elif category == "target":
                result = {"target_missing": target_missing, "count": len(target_missing)}
            elif category == "paraphrased_native":
                result = {"paraphrased_native_missing": paraphrased_native_missing, "count": len(paraphrased_native_missing)}
            else:  # all
                result = {
                    "native_missing": native_missing,
                    "target_missing": target_missing,
                    "paraphrased_native_missing": paraphrased_native_missing,
                    "total_count": len(native_missing) + len(target_missing) + len(paraphrased_native_missing),
                }

            logger.info(f"Found missing translations: native={len(native_missing)}, target={len(target_missing)}, paraphrased={len(paraphrased_native_missing)}")
            return json.dumps(result, indent=2, ensure_ascii=False)

        except Exception as e:
            error_msg = f"Failed to list missing translations: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return json.dumps({"error": error_msg})

list_missing_translations_tool = function_tool(list_missing_translations)

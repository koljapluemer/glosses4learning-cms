"""Tool for listing glosses not yet checked for splitting into parts."""

from __future__ import annotations

import json
from typing import Annotated

from agents.run_context import RunContextWrapper
from agents.tool import function_tool

from agent.logging_config import LogContext
from src.shared.tree import SPLIT_LOG_MARKER, collect_situation_stats

def list_missing_parts(
    ctx: RunContextWrapper,
    situation_ref: Annotated[str | None, "Situation reference. If None, uses current situation."] = None,
) -> str:
    """
    List glosses that haven't been checked for splitting into parts.

    Returns glosses that:
    1. Don't have any parts defined, AND
    2. Don't have the SPLIT_CONSIDERED_UNNECESSARY log marker

    These are glosses that the agent should evaluate for potential splitting.

    Args:
        situation_ref: Situation reference (uses context if None)

    Returns:
        JSON string with list of gloss references and content

    Example Output:
        {
            "count": 5,
            "glosses": [
                {"ref": "eng:I run away", "content": "I run away"},
                {"ref": "deu:Guten Tag", "content": "Guten Tag"},
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

    with LogContext(logger, tool="list_missing_parts", situation_ref=situation_ref):
        logger.info(f"Listing glosses missing parts for {situation_ref}")

        try:
            situation = storage.resolve_reference(situation_ref)
            if not situation:
                return json.dumps({"error": f"Situation not found: {situation_ref}"})

            stats = collect_situation_stats(storage, situation, native_language, target_language)
            parts_missing_refs = list(stats.get("parts_missing", []))

            # Load gloss details
            glosses = []
            for ref in parts_missing_refs:
                gloss = storage.resolve_reference(ref)
                if gloss:
                    # Double-check: no parts and no split marker
                    has_parts = gloss.parts and len(gloss.parts) > 0
                    has_marker = False
                    if gloss.logs:
                        has_marker = any(SPLIT_LOG_MARKER in str(v) for v in gloss.logs.values())

                    if not has_parts and not has_marker:
                        glosses.append({
                            "ref": ref,
                            "content": gloss.content,
                            "language": gloss.language,
                        })

            result = {
                "count": len(glosses),
                "glosses": glosses,
            }

            logger.info(f"Found {len(glosses)} glosses missing parts")
            return json.dumps(result, indent=2, ensure_ascii=False)

        except Exception as e:
            error_msg = f"Failed to list missing parts: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return json.dumps({"error": error_msg})

list_missing_parts_tool = function_tool(list_missing_parts)

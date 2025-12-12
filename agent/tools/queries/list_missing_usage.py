"""Tool for listing glosses not yet checked for usage examples."""

from __future__ import annotations

import json
from typing import Annotated

from agents import RunContextWrapper, function_tool

from agent.logging_config import LogContext
from src.shared.tree import collect_situation_stats

@function_tool
def list_missing_usage(
    ctx: RunContextWrapper,
    situation_ref: Annotated[str | None, "Situation reference. If None, uses current situation."] = None,
) -> str:
    """
    List glosses that haven't been checked for usage examples.

    Returns glosses that:
    1. Don't have any usage examples defined, AND
    2. Don't have the USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE log marker

    These are glosses that the agent should evaluate for potential usage examples.

    Args:
        situation_ref: Situation reference (uses context if None)

    Returns:
        JSON string with list of gloss references and content

    Example Output:
        {
            "count": 3,
            "glosses": [
                {"ref": "eng:tree", "content": "tree"},
                {"ref": "deu:Baum", "content": "Baum"},
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

    with LogContext(logger, tool="list_missing_usage", situation_ref=situation_ref):
        logger.info(f"Listing glosses missing usage examples for {situation_ref}")

        try:
            situation = storage.resolve_reference(situation_ref)
            if not situation:
                return json.dumps({"error": f"Situation not found: {situation_ref}"})

            stats = collect_situation_stats(storage, situation, native_language, target_language)
            usage_missing_refs = list(stats.get("usage_missing", []))

            # Load gloss details
            glosses = []
            for ref in usage_missing_refs:
                gloss = storage.resolve_reference(ref)
                if gloss:
                    # Double-check: no usage examples and no impossible marker
                    has_examples = gloss.usage_examples and len(gloss.usage_examples) > 0
                    has_marker = False
                    if gloss.logs:
                        has_marker = any("USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE" in str(v) for v in gloss.logs.values())

                    if not has_examples and not has_marker:
                        glosses.append({
                            "ref": ref,
                            "content": gloss.content,
                            "language": gloss.language,
                        })

            result = {
                "count": len(glosses),
                "glosses": glosses,
            }

            logger.info(f"Found {len(glosses)} glosses missing usage examples")
            return json.dumps(result, indent=2, ensure_ascii=False)

        except Exception as e:
            error_msg = f"Failed to list missing usage examples: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return json.dumps({"error": error_msg})

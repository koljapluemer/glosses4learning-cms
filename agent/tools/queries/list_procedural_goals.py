"""Tool for listing procedural paraphrase expression goals."""

from __future__ import annotations

import json
from typing import Annotated

from agents.run_context import RunContextWrapper
from agents.tool import function_tool

from agent.logging_config import LogContext
from src.shared.validation import get_goals_by_type

def list_procedural_goals(
    ctx: RunContextWrapper,
    situation_ref: Annotated[str | None, "Situation reference. If None, uses current situation."] = None,
) -> str:
    """
    List all procedural paraphrase expression goals in a situation.

    Procedural goals are communicative intents in the native language that
    describe what the learner wants to express in the target language.

    They are tagged with "eng:procedural-paraphrase-expression-goal" and
    "eng:paraphrase".

    Args:
        situation_ref: Situation reference (uses context if None)

    Returns:
        JSON string with list of procedural goal references and content

    Example Output:
        {
            "count": 3,
            "goals": [
                {"ref": "eng:ask for help", "content": "ask for help"},
                {"ref": "eng:express gratitude", "content": "express gratitude"},
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

    with LogContext(logger, tool="list_procedural_goals", situation_ref=situation_ref):
        logger.info(f"Listing procedural goals for {situation_ref}")

        try:
            situation = storage.resolve_reference(situation_ref)
            if not situation:
                return json.dumps({"error": f"Situation not found: {situation_ref}"})

            goals = get_goals_by_type(storage, situation, native_language, target_language, "procedural")

            result = {
                "count": len(goals),
                "goals": [
                    {
                        "ref": f"{g.language}:{g.slug}",
                        "content": g.content,
                        "tags": g.tags or [],
                    }
                    for g in goals
                ],
            }

            logger.info(f"Found {len(goals)} procedural goals")
            return json.dumps(result, indent=2, ensure_ascii=False)

        except Exception as e:
            error_msg = f"Failed to list procedural goals: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return json.dumps({"error": error_msg})

list_procedural_goals_tool = function_tool(list_procedural_goals)

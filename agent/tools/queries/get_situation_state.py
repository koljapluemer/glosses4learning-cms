"""Tool for getting comprehensive situation state and validation information."""

from __future__ import annotations

import json
from typing import Annotated

from agents.run_context import RunContextWrapper
from agents.tool import function_tool

from agent.logging_config import LogContext
from src.shared.tree import build_goal_nodes, collect_situation_stats, detect_goal_type, evaluate_goal_state
from src.shared.validation import assess_goals_state

def get_situation_state(
    ctx: RunContextWrapper,
    situation_ref: Annotated[str | None, "Situation reference (format: 'lang:slug'). If None, uses current situation from context."] = None,
) -> str:
    """
    Get comprehensive state information about a learning situation.

    This is the most important query tool for the agent. It provides a complete
    assessment of the situation's current state including:
    - Goal counts and their red/yellow/green states
    - Detailed validation logs for each goal
    - Statistics about missing translations, parts, usage examples
    - Specific action items for improvement

    The agent should call this tool frequently to guide its decisions about
    what content to create next.

    Args:
        situation_ref: Reference to situation (uses context situation if None)

    Returns:
        JSON string with comprehensive state information

    Example Output:
        {
            "situation_ref": "eng:at-the-airport",
            "total_goals": 10,
            "red_goals": 3,
            "yellow_goals": 5,
            "green_goals": 2,
            "procedural_goal_count": 6,
            "understanding_goal_count": 4,
            "stats": {
                "native_missing": [...],
                "target_missing": [...],
                ...
            },
            "goal_states": {
                "eng:ask for help": {"state": "red", "log": "..."},
                ...
            },
            "summary": "3 red goals need attention. Focus on adding translations and parts."
        }
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger
    native_language = agent_ctx.native_language
    target_language = agent_ctx.target_language

    # Use context situation if not provided
    if situation_ref is None:
        situation_ref = agent_ctx.situation_ref

    with LogContext(logger, tool="get_situation_state", situation_ref=situation_ref):
        logger.info(f"Getting state for situation {situation_ref}")

        try:
            # Load situation
            situation = storage.resolve_reference(situation_ref)
            if not situation:
                error = f"Situation not found: {situation_ref}"
                logger.error(error)
                return json.dumps({"error": error})

            # Collect statistics
            stats = collect_situation_stats(storage, situation, native_language, target_language)

            # Assess goal states
            assessment = assess_goals_state(storage, situation, native_language, target_language)

            # Count goal types
            procedural_count = 0
            understanding_count = 0
            for ref in situation.children:
                gloss = storage.resolve_reference(ref)
                if not gloss:
                    continue
                goal_type = detect_goal_type(gloss, native_language, target_language)
                if goal_type == "procedural":
                    procedural_count += 1
                elif goal_type == "understanding":
                    understanding_count += 1

            total_goals = procedural_count + understanding_count
            red_count = len(assessment["red_goals"])
            yellow_count = len(assessment["yellow_goals"])
            green_count = len(assessment["green_goals"])

            # Generate summary
            if red_count > 0:
                summary = f"{red_count} red goals need attention. Focus on adding translations and parts."
            elif yellow_count > 0:
                summary = f"{yellow_count} yellow goals can be improved. Add more translations and usage examples."
            elif green_count > 0:
                summary = f"All {green_count} goals are green! Situation is well covered."
            else:
                summary = "No goals found. Start by adding procedural and understanding goals."

            result = {
                "situation_ref": situation_ref,
                "total_goals": total_goals,
                "red_goals": red_count,
                "yellow_goals": yellow_count,
                "green_goals": green_count,
                "procedural_goal_count": procedural_count,
                "understanding_goal_count": understanding_count,
                "red_goal_refs": assessment["red_goals"],
                "yellow_goal_refs": assessment["yellow_goals"],
                "green_goal_refs": assessment["green_goals"],
                "stats": {
                    "native_missing": list(stats.get("native_missing", [])),
                    "target_missing": list(stats.get("target_missing", [])),
                    "parts_missing": list(stats.get("parts_missing", [])),
                    "usage_missing": list(stats.get("usage_missing", [])),
                },
                "goal_states": assessment["detailed_logs"],
                "summary": summary,
            }

            logger.info(f"State: {red_count} red, {yellow_count} yellow, {green_count} green")
            return json.dumps(result, indent=2, ensure_ascii=False)

        except Exception as e:
            error_msg = f"Failed to get situation state: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return json.dumps({"error": error_msg})

get_situation_state_tool = function_tool(get_situation_state)

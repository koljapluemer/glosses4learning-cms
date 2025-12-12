"""Tool for generating understanding expression goals using LLM."""

from __future__ import annotations

import json
from typing import Annotated

from agents.run_context import RunContextWrapper
from agents.tool import function_tool

from agent.config import TEMPERATURE_CREATIVE
from agent.logging_config import LogContext
from src.shared.llm_client import get_openai_client

# Configuration
MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = TEMPERATURE_CREATIVE  # 0.7
SYSTEM_PROMPT = "You create expressions in the target language that a learner needs to understand in various situations."
USER_PROMPT_TEMPLATE = """Generate {num} expressions in {target_language} for the situation: "{situation_content}".

These are things a learner might HEAR or encounter in {target_language} and need to UNDERSTAND.

Examples:
- Questions people might ask them
- Statements they might hear
- Signs or announcements they might read

Requirements:
- Natural, native expressions in {target_language}
- Relevant to the situation
- Practical and commonly used

{context_text}

Return JSON with a 'goals' array of strings."""

RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "goal_list",
        "schema": {
            "type": "object",
            "properties": {
                "goals": {
                    "type": "array",
                    "items": {"type": "string"},
                }
            },
            "required": ["goals"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}


def generate_understanding_goals(
    ctx: RunContextWrapper,
    situation_ref: Annotated[str | None, "Situation reference. If None, uses current situation."] = None,
    num_goals: Annotated[int, "Number of goals to generate"] = 5,
    extra_context: Annotated[str, "Optional extra context for generation"] = "",
) -> str:
    """
    Generate understanding expression goals for a situation.

    Creates target language expressions that a learner might encounter and need
    to comprehend in the situation.

    The agent should review the generated goals and selectively add appropriate
    ones using add_gloss_as_understanding_goal.

    Args:
        situation_ref: Reference to situation (uses context if None)
        num_goals: Number of goals to generate (default: 5)
        extra_context: Optional additional context to guide generation

    Returns:
        JSON string with array of generated goals

    Example Output:
        {
            "goals": [
                "Wo ist die Toilette?",
                "Der Flug hat Verspätung",
                "Bitte folgen Sie mir"
            ],
            "count": 3,
            "message": "Generated 3 understanding goals."
        }
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger
    target_language = agent_ctx.target_language

    if situation_ref is None:
        situation_ref = agent_ctx.situation_ref

    with LogContext(logger, tool="generate_understanding_goals", situation_ref=situation_ref):
        logger.info(f"Generating {num_goals} understanding goals for {situation_ref}")

        try:
            situation = storage.resolve_reference(situation_ref)
            if not situation:
                error = f"Situation not found: {situation_ref}"
                logger.error(error)
                return json.dumps({"error": error})

            context_text = f"Additional context: {extra_context}" if extra_context else ""
            prompt = USER_PROMPT_TEMPLATE.format(
                num=num_goals,
                target_language=target_language,
                situation_content=situation.content,
                context_text=context_text,
            )

            client = get_openai_client(agent_ctx.api_key)
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=TEMPERATURE,
                max_tokens=500,
                response_format=RESPONSE_SCHEMA,
            )

            content = response.choices[0].message.content.strip()
            parsed = json.loads(content)
            goals = parsed.get("goals", []) if isinstance(parsed, dict) else []
            goals = [g.strip() for g in goals if isinstance(g, str) and g.strip()]

            logger.info(f"Generated {len(goals)} understanding goals")

            return json.dumps({
                "goals": goals,
                "count": len(goals),
                "message": f"Generated {len(goals)} understanding goals. Review and add desired goals using add_gloss_as_understanding_goal."
            }, indent=2, ensure_ascii=False)

        except Exception as e:
            error_msg = f"LLM call failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return json.dumps({"error": error_msg})

generate_understanding_goals_tool = function_tool(generate_understanding_goals)

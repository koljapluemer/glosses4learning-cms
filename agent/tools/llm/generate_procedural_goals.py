"""Tool for generating procedural paraphrase expression goals using LLM."""

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
SYSTEM_PROMPT = "You create practical expression goals a learner wants to express in the native language."
USER_PROMPT_TEMPLATE = """Generate {num} paraphrased expressions in {native_language} for the situation: "{situation_content}".

These are procedural descriptions in the learner's native language of things they might want to express in {target_language}.

Requirements:
- Formulate as standalone flashcards that make sense on their own
- Use descriptors instead of dangling pronouns (e.g., "ask your friend" not "ask them")
- Examples: "ask where something is", "express gratitude", "ask if the person you're cooking with needs help"

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


def generate_procedural_goals(
    ctx: RunContextWrapper,
    situation_ref: Annotated[str | None, "Situation reference. If None, uses current situation."] = None,
    num_goals: Annotated[int, "Number of goals to generate"] = 5,
    extra_context: Annotated[str, "Optional extra context for generation"] = "",
) -> str:
    """
    Generate procedural paraphrase expression goals for a situation.

    Creates communicative goal expressions in the native language that describe
    what a learner might want to say in the target language.

    The agent should review the generated goals and selectively add appropriate
    ones using add_gloss_as_procedural_goal.

    Args:
        situation_ref: Reference to situation (uses context if None)
        num_goals: Number of goals to generate (default: 5)
        extra_context: Optional additional context to guide generation

    Returns:
        JSON string with array of generated goals

    Example Output:
        {
            "goals": [
                "ask where something is",
                "express gratitude",
                "request help with a task"
            ],
            "count": 3,
            "message": "Generated 3 procedural goals. Review and add desired goals."
        }
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger
    native_language = agent_ctx.native_language
    target_language = agent_ctx.target_language

    if situation_ref is None:
        situation_ref = agent_ctx.situation_ref

    with LogContext(logger, tool="generate_procedural_goals", situation_ref=situation_ref):
        logger.info(f"Generating {num_goals} procedural goals for {situation_ref}")

        try:
            # Load situation
            situation = storage.resolve_reference(situation_ref)
            if not situation:
                error = f"Situation not found: {situation_ref}"
                logger.error(error)
                return json.dumps({"error": error})

            # Build prompt
            context_text = f"Additional context: {extra_context}" if extra_context else ""
            prompt = USER_PROMPT_TEMPLATE.format(
                num=num_goals,
                native_language=native_language,
                target_language=target_language,
                situation_content=situation.content,
                context_text=context_text,
            )

            # Call LLM
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

            # Clean and validate
            goals = [g.strip() for g in goals if isinstance(g, str) and g.strip()]

            logger.info(f"Generated {len(goals)} goals")

            return json.dumps({
                "goals": goals,
                "count": len(goals),
                "message": f"Generated {len(goals)} procedural goals. Review and add desired goals using add_gloss_as_procedural_goal."
            }, indent=2, ensure_ascii=False)

        except Exception as e:
            error_msg = f"LLM call failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return json.dumps({"error": error_msg})

generate_procedural_goals_tool = function_tool(generate_procedural_goals)

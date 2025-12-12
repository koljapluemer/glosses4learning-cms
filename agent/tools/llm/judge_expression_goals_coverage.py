"""Tool for judging whether procedural expression goals adequately cover a situation."""

from __future__ import annotations

import json
import random
from typing import Annotated

from agents import RunContextWrapper, function_tool

from agent.logging_config import LogContext
from src.shared.llm_client import get_openai_client

# Configuration constants
MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0.0
MAX_GOALS_FOR_JUDGMENT = 30

SYSTEM_PROMPT = """You judge whether a set of procedural expression goals (things a learner wants to say) adequately covers a learning situation.

Consider: Are the most important communicative intents covered? Are there obvious gaps?"""

USER_PROMPT_TEMPLATE = """Situation: {situation_description}

Procedural expression goals (things the learner wants to express):
{goals_text}

Judge whether these goals provide good coverage of what a learner might want to say in this situation.

First provide a judgment sentence explaining your assessment, then a rating from 1-10 (1=very poor coverage, 10=excellent coverage).

Return JSON with "judgment" (string) and "rating" (integer 1-10)."""


@function_tool
def judge_expression_goals_coverage(
    ctx: RunContextWrapper,
    situation_ref: Annotated[str, "Situation reference (format: 'lang:slug')"],
    goal_contents: Annotated[list[str], "List of procedural goal contents to judge"],
) -> str:
    """
    Judge whether procedural expression goals adequately cover the situation.

    Evaluates if the set of "things to say" goals provides good coverage of
    what a learner might want to express in the situation.

    If more than 30 goals provided, randomly samples 30 for judgment.

    Args:
        situation_ref: Reference to the situation being judged
        goal_contents: List of procedural goal content strings

    Returns:
        JSON string with judgment and rating, or error message

    Example:
        judge_expression_goals_coverage(ctx, "eng:at-restaurant", ["I want water", "Where is the bathroom"])
        -> '{"judgment": "Basic coverage but missing common needs", "rating": 5}'
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger
    api_key = agent_ctx.api_key

    with LogContext(logger, tool="judge_expression_goals_coverage", situation_ref=situation_ref):
        logger.info(f"Judging expression goals coverage for {situation_ref} ({len(goal_contents)} goals)")

        try:
            # Load situation
            situation = storage.resolve_reference(situation_ref)
            if not situation:
                error_msg = f"Situation not found: {situation_ref}"
                logger.error(error_msg)
                return f"Error: {error_msg}"

            # Sample goals if too many
            if len(goal_contents) > MAX_GOALS_FOR_JUDGMENT:
                logger.info(f"Sampling {MAX_GOALS_FOR_JUDGMENT} from {len(goal_contents)} goals")
                goal_contents = random.sample(goal_contents, MAX_GOALS_FOR_JUDGMENT)

            # Build prompt
            goals_text = "\n".join(f"- {content}" for content in goal_contents)
            prompt = USER_PROMPT_TEMPLATE.format(
                situation_description=situation.content,
                goals_text=goals_text,
            )

            # Call LLM
            client = get_openai_client(api_key)
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=TEMPERATURE,
                max_tokens=300,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "coverage_judgment",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "judgment": {"type": "string"},
                                "rating": {"type": "integer", "minimum": 1, "maximum": 10},
                            },
                            "required": ["judgment", "rating"],
                            "additionalProperties": False,
                        },
                        "strict": True,
                    },
                },
            )

            content = response.choices[0].message.content.strip()
            data = json.loads(content)

            logger.info(f"Coverage judgment: {data.get('rating')}/10")
            return json.dumps(data)

        except Exception as e:
            error_msg = f"Failed to judge expression goals coverage: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

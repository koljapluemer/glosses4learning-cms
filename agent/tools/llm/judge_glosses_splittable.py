"""Tool for judging whether glosses can be split into parts."""

from __future__ import annotations

import json
from typing import Annotated

from agents.run_context import RunContextWrapper
from agents.tool import function_tool

from agent.logging_config import LogContext
from src.shared.llm_client import get_openai_client

# Configuration constants
MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0.0

SYSTEM_PROMPT = """You judge if expressions can be split into learnable parts.

Single words cannot be split (false).
Multi-word phrases or expressions can be split into component words or sub-expressions (true)."""

USER_PROMPT_TEMPLATE = """For each gloss below, judge if it can be reasonably split into learnable parts like words or sub-expressions (true), or if it's already a single atomic unit (false).

Glosses to judge:
{glosses_text}

Return JSON with a "judgments" object mapping each gloss content to a boolean."""


def judge_glosses_splittable(
    ctx: RunContextWrapper,
    gloss_refs: Annotated[list[str], "List of gloss references to judge (format: ['lang:slug', ...])"],
) -> str:
    """
    Judge whether glosses can be split into component parts.

    Returns a dict mapping gloss_ref → boolean indicating if the gloss is a multi-word
    expression that can be split (true) or a single atomic word (false).

    Args:
        gloss_refs: List of gloss references to judge

    Returns:
        JSON string with judgments dict, or error message

    Example:
        judge_glosses_splittable(ctx, ["eng:tree", "eng:I run away"])
        -> '{"eng:tree": false, "eng:I run away": true}'
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger
    api_key = agent_ctx.api_key

    with LogContext(logger, tool="judge_glosses_splittable"):
        logger.info(f"Judging {len(gloss_refs)} glosses for splittability")

        try:
            # Load glosses and build content map
            gloss_map = {}
            for ref in gloss_refs:
                gloss = storage.resolve_reference(ref)
                if gloss:
                    gloss_map[ref] = gloss.content

            if not gloss_map:
                return json.dumps({})

            # Build prompt with gloss contents
            glosses_text = "\n".join(f"- {content}" for content in gloss_map.values())
            prompt = USER_PROMPT_TEMPLATE.format(glosses_text=glosses_text)

            # Call LLM
            client = get_openai_client(api_key)
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=TEMPERATURE,
                max_tokens=500,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "splittability_judgments",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "judgments": {
                                    "type": "object",
                                    "additionalProperties": {"type": "boolean"},
                                }
                            },
                            "required": ["judgments"],
                            "additionalProperties": False,
                        },
                        "strict": True,
                    },
                },
            )

            content = response.choices[0].message.content.strip()
            data = json.loads(content)
            judgments_by_content = data.get("judgments", {})

            # Map back to gloss refs
            result = {}
            for ref, gloss_content in gloss_map.items():
                result[ref] = judgments_by_content.get(gloss_content, False)

            logger.info(f"Judged {len(result)} glosses for splittability")
            return json.dumps(result)

        except Exception as e:
            error_msg = f"Failed to judge gloss splittability: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

judge_glosses_splittable_tool = function_tool(judge_glosses_splittable)

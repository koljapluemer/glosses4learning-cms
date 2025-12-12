"""Tool for judging whether glosses can usefully have usage examples."""

from __future__ import annotations

import json
from typing import Annotated

from agents import RunContextWrapper, function_tool

from agent.logging_config import LogContext
from src.shared.llm_client import get_openai_client

# Configuration constants
MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0.0

SYSTEM_PROMPT = """You judge whether glosses are suitable for usage examples.

Words and short phrases can usefully be demonstrated in example sentences.
Complete sentences or long expressions cannot - they ARE the examples."""

USER_PROMPT_TEMPLATE = """For each gloss below, judge if it's a word or short phrase that can usefully be used as a building block in an example sentence (true), or if it's already a complete sentence/standalone utterance (false).

Glosses to judge:
{glosses_text}

Return JSON with a "judgments" object mapping each gloss content to a boolean."""


@function_tool
def judge_usage_examples_useful(
    ctx: RunContextWrapper,
    gloss_refs: Annotated[list[str], "List of gloss references to judge (format: ['lang:slug', ...])"],
) -> str:
    """
    Judge whether glosses can usefully have usage examples.

    Returns a dict mapping gloss_ref → boolean indicating if the gloss is a word/phrase
    that can benefit from example sentences (true) or is already a complete sentence (false).

    Args:
        gloss_refs: List of gloss references to judge

    Returns:
        JSON string with judgments dict, or error message

    Example:
        judge_usage_examples_useful(ctx, ["eng:tree", "eng:The tree is green"])
        -> '{"eng:tree": true, "eng:The tree is green": false}'
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger
    api_key = agent_ctx.api_key

    with LogContext(logger, tool="judge_usage_examples_useful"):
        logger.info(f"Judging {len(gloss_refs)} glosses for usage example suitability")

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
                        "name": "usage_example_judgments",
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

            logger.info(f"Judged {len(result)} glosses")
            return json.dumps(result)

        except Exception as e:
            error_msg = f"Failed to judge usage example suitability: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

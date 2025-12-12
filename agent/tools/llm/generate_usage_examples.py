"""Tool for generating usage example sentences for a gloss."""

from __future__ import annotations

import json
from typing import Annotated

from agents.run_context import RunContextWrapper
from agents.tool import function_tool

from agent.logging_config import LogContext
from src.shared.languages import get_ai_note
from src.shared.llm_client import get_openai_client

# Configuration constants
MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0.2

SYSTEM_PROMPT = """You generate concise usage example sentences for language learning.

Create natural, practical sentences that demonstrate how the word or phrase is used in context."""

USER_PROMPT_TEMPLATE = """Generate {num_examples} example sentences that use the {language} word/phrase: "{content}"

The gloss should appear naturally in each sentence. Keep sentences practical and relevant for learners.

{ai_note}

Return JSON with an "examples" array of sentence strings."""


def generate_usage_examples(
    ctx: RunContextWrapper,
    gloss_ref: Annotated[str, "Gloss reference for word/phrase to demonstrate (format: 'lang:slug')"],
    num_examples: Annotated[int, "Number of example sentences to generate"] = 3,
) -> str:
    """
    Generate usage example sentences for a word or phrase.

    Creates example sentences that demonstrate how the gloss is used in context.
    The gloss should appear in the parts array of the generated examples.

    Args:
        gloss_ref: Reference to the gloss to create examples for
        num_examples: Number of example sentences to generate (default: 3)

    Returns:
        JSON string with list of example sentences, or error message

    Example:
        generate_usage_examples(ctx, "eng:tree", 3)
        -> '["The tree is very tall", "We sat under the tree", "Birds live in the tree"]'
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger
    api_key = agent_ctx.api_key

    with LogContext(logger, tool="generate_usage_examples", gloss_ref=gloss_ref):
        logger.info(f"Generating {num_examples} usage examples for {gloss_ref}")

        try:
            # Load gloss
            gloss = storage.resolve_reference(gloss_ref)
            if not gloss:
                error_msg = f"Gloss not found: {gloss_ref}"
                logger.error(error_msg)
                return f"Error: {error_msg}"

            # Get language AI note
            ai_note = get_ai_note(gloss.language)
            ai_note_text = f"Language notes: {ai_note}" if ai_note else ""

            # Build prompt
            prompt = USER_PROMPT_TEMPLATE.format(
                num_examples=num_examples,
                language=gloss.language,
                content=gloss.content,
                ai_note=ai_note_text,
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
                max_tokens=500,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "usage_examples",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "examples": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                }
                            },
                            "required": ["examples"],
                            "additionalProperties": False,
                        },
                        "strict": True,
                    },
                },
            )

            content = response.choices[0].message.content.strip()
            data = json.loads(content)
            examples = data.get("examples", [])

            if not examples:
                logger.warning(f"No examples generated for {gloss_ref}")
                return json.dumps([])

            logger.info(f"Generated {len(examples)} examples for {gloss_ref}")
            return json.dumps(examples)

        except Exception as e:
            error_msg = f"Failed to generate usage examples: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

generate_usage_examples_tool = function_tool(generate_usage_examples)

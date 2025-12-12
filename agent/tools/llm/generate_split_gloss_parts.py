"""Tool for splitting a gloss into component parts."""

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

SYSTEM_PROMPT = """You are a concise linguistic decomposition assistant.

Break expressions into learnable component parts - words or meaningful sub-expressions."""

USER_PROMPT_TEMPLATE = """Take this {language} expression or phrase and break it up into parts that can be learned on their own.

Expression: {content}

Return a JSON object with a 'parts' array of strings. Avoid repetition.

{ai_note}"""


def generate_split_gloss_parts(
    ctx: RunContextWrapper,
    gloss_ref: Annotated[str, "Gloss reference to split into parts (format: 'lang:slug')"],
) -> str:
    """
    Split a gloss into component parts.

    Takes a multi-word expression or phrase and breaks it into learnable components
    (words or meaningful sub-expressions) in the same language.

    Args:
        gloss_ref: Reference to the gloss to split

    Returns:
        JSON string with list of part strings, or error message

    Example:
        generate_split_gloss_parts(ctx, "eng:I run away")
        -> '["I", "run", "away"]'
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger
    api_key = agent_ctx.api_key

    with LogContext(logger, tool="generate_split_gloss_parts", gloss_ref=gloss_ref):
        logger.info(f"Splitting {gloss_ref} into parts")

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
                max_tokens=200,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "parts_list",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "parts": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                }
                            },
                            "required": ["parts"],
                            "additionalProperties": False,
                        },
                        "strict": True,
                    },
                },
            )

            content = response.choices[0].message.content.strip()
            data = json.loads(content)
            parts = data.get("parts", [])

            # Clean and filter parts
            parts = [p.strip() for p in parts if isinstance(p, str) and p.strip()]

            if not parts:
                logger.warning(f"No parts generated for {gloss_ref}")
                return json.dumps([])

            logger.info(f"Split {gloss_ref} into {len(parts)} parts")
            return json.dumps(parts)

        except Exception as e:
            error_msg = f"Failed to split gloss into parts: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

generate_split_gloss_parts_tool = function_tool(generate_split_gloss_parts)

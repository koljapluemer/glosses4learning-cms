"""Tool for generating usage notes for target language glosses."""

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

SYSTEM_PROMPT = """You create concise usage notes in the native language explaining how target language words/phrases are used.

Focus on: formality level, context, special situations, or any notable usage patterns."""

USER_PROMPT_TEMPLATE = """For each {target_language} gloss below, provide a brief usage note in {native_language} explaining when/how it's used, its formality level, or any special considerations.

Keep notes concise (a few words to one sentence).

Glosses:
{glosses_text}

{ai_note}

Return JSON with a "notes" object mapping each gloss content to its usage note string."""


def generate_usage_notes(
    ctx: RunContextWrapper,
    gloss_refs: Annotated[list[str], "List of target language gloss references (format: ['lang:slug', ...])"],
) -> str:
    """
    Generate usage notes for target language glosses.

    Creates brief notes in the native language explaining when/how each target
    language gloss is used, formality level, or special usage considerations.

    Args:
        gloss_refs: List of target language gloss references

    Returns:
        JSON string with notes dict mapping gloss_ref → note text, or error message

    Example:
        generate_usage_notes(ctx, ["deu:Tschüss", "deu:Auf Wiedersehen"])
        -> '{"deu:Tschüss": "used in casual situations", "deu:Auf Wiedersehen": "semi-formal"}'
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger
    api_key = agent_ctx.api_key
    native_language = agent_ctx.native_language
    target_language = agent_ctx.target_language

    with LogContext(logger, tool="generate_usage_notes"):
        logger.info(f"Generating usage notes for {len(gloss_refs)} target glosses")

        try:
            # Load glosses and build content map
            gloss_map = {}
            for ref in gloss_refs:
                gloss = storage.resolve_reference(ref)
                if gloss and gloss.language == target_language:
                    gloss_map[ref] = gloss.content

            if not gloss_map:
                return json.dumps({})

            # Get language AI note for target language
            ai_note = get_ai_note(target_language)
            ai_note_text = f"Language notes for {target_language}: {ai_note}" if ai_note else ""

            # Build prompt with gloss contents
            glosses_text = "\n".join(f"- {content}" for content in gloss_map.values())
            prompt = USER_PROMPT_TEMPLATE.format(
                target_language=target_language,
                native_language=native_language,
                glosses_text=glosses_text,
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
                        "name": "usage_notes",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "notes": {
                                    "type": "object",
                                    "additionalProperties": {"type": "string"},
                                }
                            },
                            "required": ["notes"],
                            "additionalProperties": False,
                        },
                        "strict": True,
                    },
                },
            )

            content = response.choices[0].message.content.strip()
            data = json.loads(content)
            notes_by_content = data.get("notes", {})

            # Map back to gloss refs
            result = {}
            for ref, gloss_content in gloss_map.items():
                note = notes_by_content.get(gloss_content, "")
                if note:
                    result[ref] = note

            logger.info(f"Generated usage notes for {len(result)} glosses")
            return json.dumps(result)

        except Exception as e:
            error_msg = f"Failed to generate usage notes: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

generate_usage_notes_tool = function_tool(generate_usage_notes)

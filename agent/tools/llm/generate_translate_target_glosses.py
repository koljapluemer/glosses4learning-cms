"""Tool for translating target language glosses to native language."""

from __future__ import annotations

import json
from typing import Annotated

from agents import RunContextWrapper, function_tool

from agent.logging_config import LogContext
from src.shared.languages import get_ai_note
from src.shared.llm_client import get_openai_client

# Configuration constants
MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0.2

SYSTEM_PROMPT = """You are a concise translation assistant for language learning glosses.

Provide accurate, practical translations that learners would find useful."""

USER_PROMPT_TEMPLATE = """Translate the following {source_language} gloss into {target_language}.

Gloss: {content}

Return a JSON object with a 'translations' array of translation strings. Keep them concise and practical.

{ai_note}"""


@function_tool
def generate_translate_target_glosses(
    ctx: RunContextWrapper,
    gloss_refs: Annotated[list[str], "List of target language gloss references to translate (format: ['lang:slug', ...])"],
) -> str:
    """
    Translate target language glosses to native language.

    Takes glosses in the target language and generates translations in the native language.
    Returns a dict mapping gloss_ref → list of translation strings.

    Args:
        gloss_refs: List of target language gloss references to translate

    Returns:
        JSON string with translations dict, or error message

    Example:
        generate_translate_target_glosses(ctx, ["deu:Baum", "deu:laufen"])
        -> '{"deu:Baum": ["tree"], "deu:laufen": ["to run", "to walk"]}'
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger
    api_key = agent_ctx.api_key
    native_language = agent_ctx.native_language

    with LogContext(logger, tool="generate_translate_target_glosses"):
        logger.info(f"Translating {len(gloss_refs)} target glosses to {native_language}")

        try:
            # Get language AI note for native language
            ai_note = get_ai_note(native_language)
            ai_note_text = f"Language notes for {native_language}: {ai_note}" if ai_note else ""

            result = {}
            client = get_openai_client(api_key)

            for ref in gloss_refs:
                gloss = storage.resolve_reference(ref)
                if not gloss:
                    logger.warning(f"Gloss not found: {ref}")
                    result[ref] = []
                    continue

                # Build prompt
                prompt = USER_PROMPT_TEMPLATE.format(
                    source_language=gloss.language,
                    target_language=native_language,
                    content=gloss.content,
                    ai_note=ai_note_text,
                )

                # Call LLM
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
                            "name": "translation_list",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "translations": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    }
                                },
                                "required": ["translations"],
                                "additionalProperties": False,
                            },
                            "strict": True,
                        },
                    },
                )

                content = response.choices[0].message.content.strip()
                data = json.loads(content)
                translations = data.get("translations", [])

                # Clean translations
                translations = [t.strip() for t in translations if isinstance(t, str) and t.strip()]
                result[ref] = translations

                logger.info(f"Translated {ref}: {len(translations)} translations")

            logger.info(f"Completed translation of {len(result)} glosses")
            return json.dumps(result)

        except Exception as e:
            error_msg = f"Failed to translate target glosses: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

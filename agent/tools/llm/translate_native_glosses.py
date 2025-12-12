"""Tool for translating native glosses to target language."""

from __future__ import annotations

import json
from typing import Annotated

from agents.run_context import RunContextWrapper
from agents.tool import function_tool

from agent.config import TEMPERATURE_TRANSLATION
from agent.logging_config import LogContext
from src.shared.languages import get_ai_note
from src.shared.llm_client import get_openai_client

# Configuration
MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = TEMPERATURE_TRANSLATION  # 0.2
SYSTEM_PROMPT = "You are a professional translator providing accurate translations between languages."
USER_PROMPT_TEMPLATE = """Translate "{content}" from {native_language} to {target_language}.

Provide 2-4 natural translations that a native speaker would use.
Include usage notes ONLY when there are important distinctions (formality, context, etc.).

{ai_note_text}

Return JSON with translations array. Each item:
- "text": the translation (REQUIRED)
- "note": usage note in {native_language}; use an empty string if not needed (REQUIRED)"""

RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "translation_list",
        "schema": {
            "type": "object",
            "properties": {
                "translations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "note": {"type": "string"},
                        },
                        "required": ["text", "note"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["translations"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}


def translate_native_glosses(
    ctx: RunContextWrapper,
    gloss_refs: Annotated[list[str], "List of native gloss references to translate"],
    batch_size: Annotated[int, "Batch size for LLM calls"] = 25,
) -> str:
    """
    Translate native language glosses to target language.

    This tool provides standard translation for native language glosses
    (not paraphrases) into the target language.

    Args:
        gloss_refs: List of native language gloss references to translate

    Returns:
        JSON string with translations for each input gloss

    Example Output:
        {
            "translations": {
                "eng:hello": [
                    {"text": "Hallo"},
                    {"text": "Guten Tag", "note": "more formal"}
                ],
                ...
            },
            "count": 1,
            "message": "Generated translations for 1 gloss."
        }
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger
    native_language = agent_ctx.native_language
    target_language = agent_ctx.target_language

    with LogContext(logger, tool="translate_native_glosses"):
        logger.info(f"Translating {len(gloss_refs)} native glosses (batch size {batch_size})")

        try:
            ai_note = get_ai_note(target_language)
            ai_note_text = f"Notes for this language: {ai_note}." if ai_note else ""

            client = get_openai_client(agent_ctx.api_key)
            results = {}

            def chunk(seq, size):
                for i in range(0, len(seq), size):
                    yield seq[i : i + size]

            for batch in chunk(gloss_refs, batch_size):
                glosses = []
                ref_map = {}
                for ref in batch:
                    gloss = storage.resolve_reference(ref)
                    if not gloss:
                        results[ref] = {"error": "Gloss not found"}
                        continue
                    glosses.append(gloss)
                    ref_map[gloss.content] = ref

                if not glosses:
                    continue

                prompt_items = "\n".join(f"- {g.content}" for g in glosses)
                prompt = (
                    f"Translate these {native_language} glosses into {target_language}.\n"
                    f"Provide 2-4 natural translations per gloss, with an optional usage note (empty string if none).\n\n"
                    f"{prompt_items}\n\n"
                    "Return JSON with 'translations': { gloss_content: [ {\"text\": str, \"note\": str}, ... ] }."
                )

                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=TEMPERATURE,
                    max_tokens=1200,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "batched_translations",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "translations": {
                                        "type": "object",
                                        "additionalProperties": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "text": {"type": "string"},
                                                    "note": {"type": "string"},
                                                },
                                                "required": ["text", "note"],
                                                "additionalProperties": False,
                                            },
                                        },
                                    }
                                },
                                "required": ["translations"],
                                "additionalProperties": False,
                            },
                            "strict": True,
                        },
                    },
                )

                content_str = response.choices[0].message.content.strip()
                parsed = json.loads(content_str)
                translations_obj = parsed.get("translations", {}) if isinstance(parsed, dict) else {}

                for gloss_content, items in translations_obj.items():
                    ref = ref_map.get(gloss_content)
                    if not ref:
                        continue
                    valid_translations = []
                    for item in items or []:
                        if (
                            isinstance(item, dict)
                            and isinstance(item.get("text"), str)
                            and item["text"].strip() != ""
                            and isinstance(item.get("note"), str)
                        ):
                            valid_translations.append(
                                {
                                    "text": item["text"].strip(),
                                    "note": item.get("note", "").strip(),
                                }
                            )
                    results[ref] = valid_translations
                    logger.info(f"Translated {ref}: {len(valid_translations)} options")

            return json.dumps({
                "translations": results,
                "count": len(results),
                "message": f"Generated translations for {len(results)} glosses. Use add_translation to add desired translations."
            }, indent=2, ensure_ascii=False)

        except Exception as e:
            error_msg = f"LLM call failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return json.dumps({"error": error_msg})

translate_native_glosses_tool = function_tool(translate_native_glosses)

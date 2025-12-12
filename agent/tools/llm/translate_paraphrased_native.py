"""Tool for translating paraphrased native expressions to target language."""

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
SYSTEM_PROMPT = """You are a specialized language assistant for translating communicative goals (paraphrases) into actual expressions.

CRITICAL: The input is NOT a phrase to translate literally. It is a COMMUNICATIVE GOAL describing what a learner wants to express.

Your task:
- Find the ACTUAL ways native speakers would EXPRESS this goal in the target language
- Return real phrases/expressions, NOT literal word-for-word translations
- Include usage notes ONLY when expressions have important context differences

Example (English → German):
Input: "express gratitude"
CORRECT: ["Danke", "Dankeschön", "Vielen Dank"]
WRONG: ["Dankbarkeit ausdrücken"] ← this is literal translation, not how people speak"""

USER_PROMPT_TEMPLATE = """Communicative goal: "{content}"
Target language: {target_language}

Find 2-4 ACTUAL expressions native speakers use to achieve this communicative goal.
Do NOT translate literally. Find how people REALLY EXPRESS this concept.
{ai_note_text}

Return JSON with translations array. Each item:
- "text": the actual expression (REQUIRED)
- "note": usage guidance in {native_language}; use an empty string if no note is needed (REQUIRED)"""

RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "translation_list_with_notes",
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


def translate_paraphrased_native(
    ctx: RunContextWrapper,
    gloss_refs: Annotated[list[str], "List of native paraphrase gloss references to translate"],
    batch_size: Annotated[int, "Batch size for LLM calls"] = 25,
) -> str:
    """
    Translate paraphrased native expressions to target language.

    This tool is specifically for translating communicative goals (paraphrases)
    into actual target language expressions that native speakers would use.

    It does NOT do literal translation - it finds how people really express
    the communicative intent.

    Args:
        gloss_refs: List of native language paraphrase references to translate

    Returns:
        JSON string with translations for each input gloss

    Example Output:
        {
            "translations": {
                "eng:express gratitude": [
                    {"text": "Danke", "note": "informal"},
                    {"text": "Vielen Dank", "note": "more emphatic"}
                ],
                ...
            },
            "count": 2,
            "message": "Generated translations for 2 paraphrases."
        }
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger
    native_language = agent_ctx.native_language
    target_language = agent_ctx.target_language

    with LogContext(logger, tool="translate_paraphrased_native"):
        logger.info(f"Translating {len(gloss_refs)} paraphrased expressions (batch size {batch_size})")

        try:
            # Get language-specific AI notes
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
                    f"Translate these communicative goals (paraphrases in {native_language}) into ACTUAL expressions in {target_language}.\n"
                    f"{prompt_items}\n\n"
                    "Return JSON with 'translations': { paraphrase_content: [ {\"text\": str, \"note\": str}, ... ] }.\n"
                    "Always include 'note' (empty string if none)."
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
                            "name": "batched_paraphrase_translations",
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
                parsed = json.loads(content_str) if content_str else {}
                translations_obj = parsed.get("translations", {}) if isinstance(parsed, dict) else {}

                for paraphrase_content, items in translations_obj.items():
                    ref = ref_map.get(paraphrase_content)
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
                            valid_translations.append({
                                "text": item["text"].strip(),
                                "note": item.get("note", "").strip(),
                            })

                    results[ref] = valid_translations
                    logger.info(f"Translated {ref}: {len(valid_translations)} expressions")

            return json.dumps({
                "translations": results,
                "count": len(results),
                "message": f"Generated translations for {len(results)} paraphrases. Use add_translation to add desired translations."
            }, indent=2, ensure_ascii=False)

        except Exception as e:
            error_msg = f"LLM call failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return json.dumps({"error": error_msg})

translate_paraphrased_native_tool = function_tool(translate_paraphrased_native)

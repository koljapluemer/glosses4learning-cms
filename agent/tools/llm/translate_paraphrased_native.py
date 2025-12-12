"""Tool for translating paraphrased native expressions to target language."""

from __future__ import annotations

import json
from typing import Annotated

from agents import RunContextWrapper, function_tool

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
- "note": usage guidance in {native_language} ONLY if needed, e.g., formality level, context (OPTIONAL)"""

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
                        "required": ["text"],
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


@function_tool
def translate_paraphrased_native(
    ctx: RunContextWrapper,
    gloss_refs: Annotated[list[str], "List of native paraphrase gloss references to translate"],
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
        logger.info(f"Translating {len(gloss_refs)} paraphrased expressions")

        try:
            # Get language-specific AI notes
            ai_note = get_ai_note(target_language)
            ai_note_text = f"Notes for this language: {ai_note}." if ai_note else ""

            client = get_openai_client(agent_ctx.api_key)
            results = {}

            for ref in gloss_refs:
                gloss = storage.resolve_reference(ref)
                if not gloss:
                    results[ref] = {"error": "Gloss not found"}
                    continue

                # Build prompt
                prompt = USER_PROMPT_TEMPLATE.format(
                    content=gloss.content,
                    target_language=target_language,
                    native_language=native_language,
                    ai_note_text=ai_note_text,
                )

                # Call LLM
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=TEMPERATURE,
                    max_tokens=300,
                    response_format=RESPONSE_SCHEMA,
                )

                content_str = response.choices[0].message.content.strip()
                parsed = json.loads(content_str)
                translations = parsed.get("translations", []) if isinstance(parsed, dict) else []

                # Validate and clean
                valid_translations = []
                for item in translations:
                    if isinstance(item, dict) and isinstance(item.get("text"), str) and item["text"].strip():
                        valid_translations.append(item)

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

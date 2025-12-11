from __future__ import annotations

import json
import logging

from prompt_toolkit.shortcuts import checkboxlist_dialog, input_dialog, message_dialog

from src.shared.storage import Gloss, GlossStorage

logger = logging.getLogger(__name__)

# AI model/prompt constants
SITUATION_MODEL = "gpt-4o-mini"
SITUATION_SYSTEM_PROMPT = "You propose concise language-learning situations."
SITUATION_USER_PROMPT = (
    "Generate {num} concise titles of language-learning situations. "
    "They should describe practical contexts like 'ordering street food' or 'meeting a stranger who appears in trouble'. "
    "Return JSON with a 'situations' array of strings."
)

SITUATION_LANGUAGE = "eng"
SITUATION_TAG = "eng:situation"


def _openai_client(api_key: str):
    try:
        from openai import OpenAI
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Install openai package: pip install openai") from exc
    return OpenAI(api_key=api_key)


def generate_situations(api_key: str, num: int, extra_context: str | None) -> list[str]:
    client = _openai_client(api_key)
    prompt = SITUATION_USER_PROMPT.format(num=num)
    if extra_context:
        prompt += f" Additional context: {extra_context}"
    resp = client.chat.completions.create(
        model=SITUATION_MODEL,
        messages=[
            {"role": "system", "content": SITUATION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.6,
        max_tokens=300,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "situation_list",
                "schema": {
                    "type": "object",
                    "properties": {"situations": {"type": "array", "items": {"type": "string"}}},
                    "required": ["situations"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        },
    )
    content = resp.choices[0].message.content.strip()  # type: ignore[index]
    try:
        parsed = json.loads(content)
        items = parsed.get("situations", []) if isinstance(parsed, dict) else []
    except Exception:
        items = []
    return [s.strip() for s in items if isinstance(s, str) and s.strip()]


def flow_add_situations_ai(storage: GlossStorage, state: dict) -> None:
    api_key = (state.get("settings") or {}).get("OPENAI_API_KEY")
    if not api_key:
        message_dialog(title="Error", text="OPENAI_API_KEY required.").run()
        return

    num_raw = input_dialog(title="How many situations?", text="Number to generate (default 5):").run()
    try:
        num = int(num_raw) if num_raw else 5
        if num <= 0:
            num = 5
    except Exception:
        num = 5

    context = input_dialog(title="Extra context (optional)", text="Provide any hints for the AI (optional):").run() or ""

    try:
        suggestions = generate_situations(api_key=api_key, num=num, extra_context=context.strip())
    except Exception as exc:  # noqa: BLE001
        logger.error("Situation generation failed: %s", exc)
        message_dialog(title="Error", text=str(exc)).run()
        return

    if not suggestions:
        message_dialog(title="Info", text="No situations generated.").run()
        return

    selection = checkboxlist_dialog(
        title="Select situations to add",
        text="Accept situations to add (stored in English).",
        values=[(s, s) for s in suggestions],
        default_values=list(suggestions),
    ).run()
    if not selection:
        return

    created = 0
    updated = 0
    for content in selection:
        existing = storage.find_gloss_by_content(SITUATION_LANGUAGE, content)
        if existing:
            tags = existing.tags or []
            if SITUATION_TAG not in tags:
                existing.tags = tags + [SITUATION_TAG]
                storage.save_gloss(existing)
                updated += 1
            continue
        storage.create_gloss(Gloss(content=content, language=SITUATION_LANGUAGE, tags=[SITUATION_TAG]))
        created += 1

    message_dialog(title="Done", text=f"Created {created}, updated {updated}.").run()

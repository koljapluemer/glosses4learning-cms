from __future__ import annotations

import json
import logging

from prompt_toolkit.shortcuts import checkboxlist_dialog, message_dialog

from src.shared.storage import Gloss, GlossStorage, attach_relation

# AI model/prompt constants (edit as needed)
GOALS_MODEL = "gpt-4o-mini"
GOALS_SYSTEM_PROMPT = "You create practical expression goals a learner wants to express in the native language."
GOALS_USER_PROMPT = (
    "Generate {num} paraphrased expressions in {native_language} for the situation: \"{situation_content}\". "
    "These are procedural descriptions in the learner's native language of things they might want to express in {target_language}. "
    "Examples for english: 'ask where something is', 'express surprise' or 'ask if the other person has moved the small fridge around yet'"
    "These will be used as standalone flashcards, so make sure they are formulated in a way that they make sense on their own."
    "For example, 'Ask them to help with this' makes no sense on its own, while 'Ask the person you're cooking with for help with your current task' does"
    "Do not use dangling pronouns such as 'Ask them...' or '...if they...', but always descriptors such as 'ask your friend...'" 
    "Return JSON with a 'goals' array of strings."
)

logger = logging.getLogger(__name__)


def _openai_client(api_key: str):
    try:
        from openai import OpenAI
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Install openai package: pip install openai") from exc
    return OpenAI(api_key=api_key)


def generate_expression_goals(api_key: str, situation_content: str, native_language: str, target_language: str, num: int) -> list[str]:
    client = _openai_client(api_key)
    prompt = GOALS_USER_PROMPT.format(
        num=num,
        native_language=native_language,
        target_language=target_language,
        situation_content=situation_content,
    )
    resp = client.chat.completions.create(
        model=GOALS_MODEL,
        messages=[
            {"role": "system", "content": GOALS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=500,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "goal_list",
                "schema": {
                    "type": "object",
                    "properties": {"goals": {"type": "array", "items": {"type": "string"}}},
                    "required": ["goals"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        },
    )
    content = resp.choices[0].message.content.strip()  # type: ignore[index]
    try:
        parsed = json.loads(content)
        goals = parsed.get("goals", []) if isinstance(parsed, dict) else []
    except Exception:
        goals = []
    return [g.strip() for g in goals if isinstance(g, str) and g.strip()]


def flow_add_goals_expression_ai(storage: GlossStorage, state: dict) -> None:
    api_key = (state.get("settings") or {}).get("OPENAI_API_KEY")
    if not api_key:
        message_dialog(title="Error", text="OPENAI_API_KEY required.").run()
        return
    situation = storage.resolve_reference(state["situation_ref"])
    if not situation:
        message_dialog(title="Error", text=f"Missing situation {state['situation_ref']}").run()
        return

    try:
        goals = generate_expression_goals(
            api_key=api_key,
            situation_content=situation.content,
            native_language=state["native_language"],
            target_language=state["target_language"],
            num=5,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Generation failed: %s", exc)
        message_dialog(title="Error", text=str(exc)).run()
        return

    if not goals:
        message_dialog(title="Info", text="No goals generated.").run()
        return

    selection = checkboxlist_dialog(
        title="Select goals to add",
        text="Accept goals to add to the situation",
        values=[(g, g) for g in goals],
    ).run()
    if not selection:
        return

    created = 0
    skipped = 0
    for goal_text in selection:
        goal_text = goal_text.strip()
        if not goal_text:
            continue
        existing = storage.find_gloss_by_content(state["native_language"], goal_text)
        if existing:
            tags = existing.tags or []
            changed = False
            if "eng:paraphrase" not in tags:
                tags.append("eng:paraphrase"); changed = True
            if "eng:procedural-paraphrase-expression-goal" not in tags:
                tags.append("eng:procedural-paraphrase-expression-goal"); changed = True
            if changed:
                existing.tags = tags
                storage.save_gloss(existing)
                created += 1
            else:
                skipped += 1
            goal = existing
        else:
            goal = storage.create_gloss(
                Gloss(content=goal_text, language=state["native_language"], tags=["eng:paraphrase", "eng:procedural-paraphrase-expression-goal"])
            )
            created += 1
        attach_relation(storage, situation, "children", goal)

    message_dialog(title="Done", text=f"Created {created}, skipped {skipped}.").run()

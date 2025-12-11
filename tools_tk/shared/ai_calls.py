from __future__ import annotations

import os
from typing import Any

try:
    from openai import OpenAI
except Exception:  # noqa: BLE001
    OpenAI = None  # type: ignore


def _client():
    if not OpenAI:
        raise RuntimeError("openai package not installed")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set")
    return OpenAI()


def generate_understand_goals(
    *,
    situation_content: str,
    target_language: str,
    num_goals: int = 5,
    context: str = "",
    model: str = "gpt-4o-mini",
) -> tuple[list[str], str | None]:
    prompt = (
        f"Generate {num_goals} understand-expression-goals in {target_language} for the situation: \"{situation_content}\". "
        "These are target language expressions learners should understand. Return JSON with a 'goals' array."
    )
    if context:
        prompt += f" Additional context: {context}"
    try:
        client = _client()
        resp = client.chat.completions.create(  # type: ignore[call-arg]
            model=model,
            messages=[
                {"role": "system", "content": "You create practical understand-expression goals for language learners."},
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
    except Exception as exc:  # noqa: BLE001
        return [], str(exc)
    try:
        import json

        parsed = json.loads(content)
        goals = parsed.get("goals", []) if isinstance(parsed, dict) else []
    except Exception:
        goals = []
    goals = [g.strip() for g in goals if isinstance(g, str) and g.strip()]
    return goals, None


def generate_procedural_goals(
    *,
    situation_content: str,
    native_language: str,
    target_language: str,
    num_goals: int = 5,
    context: str = "",
    model: str = "gpt-4o-mini",
) -> tuple[list[str], str | None]:
    prompt = (
        f"Generate {num_goals} procedural-paraphrase-expression-goals in {native_language} for the situation: \"{situation_content}\"."
        f" These are procedural descriptions in {native_language} of things someone might want to do in {target_language}. "
        "Return JSON with a 'goals' array."
    )
    if context:
        prompt += f" Additional context: {context}"
    try:
        client = _client()
        resp = client.chat.completions.create(  # type: ignore[call-arg]
            model=model,
            messages=[
                {"role": "system", "content": "You create procedural paraphrase goals for language learners."},
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
    except Exception as exc:  # noqa: BLE001
        return [], str(exc)
    try:
        import json

        parsed = json.loads(content)
        goals = parsed.get("goals", []) if isinstance(parsed, dict) else []
    except Exception:
        goals = []
    goals = [g.strip() for g in goals if isinstance(g, str) and g.strip()]
    return goals, None

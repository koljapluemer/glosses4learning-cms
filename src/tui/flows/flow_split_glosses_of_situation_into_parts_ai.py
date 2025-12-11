from __future__ import annotations

import json
import logging
from datetime import datetime

from prompt_toolkit.shortcuts import checkboxlist_dialog, message_dialog, ProgressBar

from src.shared.storage import GlossStorage, attach_relation
from src.shared.tree import collect_situation_stats, SPLIT_LOG_MARKER

# AI model/prompt constants
JUDGE_MODEL = "gpt-4o-mini"
JUDGE_SYSTEM_PROMPT = "You judge if expressions can be split into learnable parts."
JUDGE_USER_PROMPT = (
    "Decide if the {language} expression '{content}' can be reasonably split into learnable parts. "
    "Return JSON with boolean field 'can_split'."
)

SPLIT_MODEL = "gpt-4o-mini"
SPLIT_SYSTEM_PROMPT = "You are a concise linguistic decomposition assistant."
SPLIT_USER_PROMPT = (
    "Take this {language} expression or phrase and break it up into parts that can be learned on their own. "
    "Return a JSON object with a 'parts' array of strings. Avoid repetition. Expression: {content}"
)

logger = logging.getLogger(__name__)


def _openai_client(api_key: str):
    try:
        from openai import OpenAI
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Install openai package: pip install openai") from exc
    return OpenAI(api_key=api_key)


def judge_can_split(api_key: str, content: str, language: str) -> bool:
    client = _openai_client(api_key)
    prompt = JUDGE_USER_PROMPT.format(language=language, content=content)
    resp = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=50,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "split_judge",
                "schema": {
                    "type": "object",
                    "properties": {"can_split": {"type": "boolean"}},
                    "required": ["can_split"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        },
    )
    content = resp.choices[0].message.content.strip()  # type: ignore[index]
    try:
        data = json.loads(content)
        return bool(data.get("can_split", False))
    except Exception:
        return False


def split_parts(api_key: str, content: str, language: str) -> list[str]:
    client = _openai_client(api_key)
    prompt = SPLIT_USER_PROMPT.format(language=language, content=content)
    resp = client.chat.completions.create(
        model=SPLIT_MODEL,
        messages=[
            {"role": "system", "content": SPLIT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=200,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "parts_list",
                "schema": {
                    "type": "object",
                    "properties": {"parts": {"type": "array", "items": {"type": "string"}}},
                    "required": ["parts"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        },
    )
    content = resp.choices[0].message.content.strip()  # type: ignore[index]
    try:
        parsed = json.loads(content)
        parts = parsed.get("parts", []) if isinstance(parsed, dict) else []
    except Exception:
        parts = []
    return [p.strip() for p in parts if isinstance(p, str) and p.strip()]


def mark_split_unnecessary(storage: GlossStorage, ref: str):
    gloss = storage.resolve_reference(ref)
    if not gloss:
        return
    logs = gloss.logs if isinstance(getattr(gloss, "logs", {}), dict) else {}
    logs[datetime.utcnow().isoformat() + "Z"] = SPLIT_LOG_MARKER
    gloss.logs = logs
    storage.save_gloss(gloss)


def flow_split_glosses_of_situation_into_parts_ai(storage: GlossStorage, state: dict):
    api_key = (state.get("settings") or {}).get("OPENAI_API_KEY")
    if not api_key:
        message_dialog(title="Error", text="OPENAI_API_KEY required.").run()
        return
    situation = storage.resolve_reference(state["situation_ref"])
    if not situation:
        message_dialog(title="Error", text=f"Missing situation {state['situation_ref']}").run()
        return

    stats = collect_situation_stats(storage, situation, state["native_language"], state["target_language"])
    refs = list(stats.get("parts_missing", []))
    if not refs:
        message_dialog(title="Info", text="No glosses need splitting.").run()
        return

    results = []
    with ProgressBar(title="Splitting glosses") as pb:
        for ref in pb(refs):
            gl = storage.resolve_reference(ref)
            if not gl:
                continue
            if not judge_can_split(api_key, gl.content, gl.language):
                mark_split_unnecessary(storage, ref)
                continue
            parts = split_parts(api_key, gl.content, gl.language)
            results.append((ref, gl.content, parts))

    added = 0
    errors: list[str] = []
    for ref, content, parts in results:
        if not parts:
            logger.info("No parts returned for %s (%s)", ref, content)
            continue
        selection = checkboxlist_dialog(
            title=ref,
            text=f"{content}\nSelect parts to attach:",
            values=[(p, p) for p in parts],
            default_values=list(parts),
        ).run()
        if selection is None:
            logger.info("User canceled selection for %s", ref)
            continue
        if not selection:
            logger.info("No parts selected for %s", ref)
            continue
        base = storage.resolve_reference(ref)
        if not base:
            errors.append(f"{ref}: missing base gloss")
            continue
        for part_text in selection:
            try:
                part_gloss = storage.ensure_gloss(base.language, part_text)
                attach_relation(storage, base, "parts", part_gloss)
                added += 1
            except Exception as exc:  # noqa: BLE001
                msg = f"{ref} :: '{part_text}' -> {exc}"
                logger.error(msg)
                errors.append(msg)

    if errors:
        message_dialog(title="Done with errors", text=f"Added {added} parts.\nSee log for errors.").run()
    else:
        message_dialog(title="Done", text=f"Added {added} parts.").run()

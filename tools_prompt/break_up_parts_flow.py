from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from prompt_toolkit.shortcuts import checkboxlist_dialog, input_dialog, message_dialog

from tools_prompt.common import checkbox_dialog_default_checked
from tools_prompt.settings_flow import ensure_api_key
from tools_tk.shared.gloss_storage import GlossStorage, attach_relation
from tools_tk.shared.situations_tree import collect_situation_stats, SPLIT_LOG_MARKER

# Models are constants (no UI selection)
JUDGE_MODEL = "gpt-4o-mini"
SPLIT_MODEL = "gpt-4o-mini"


def mark_split_unnecessary(storage: GlossStorage, ref: str):
    gloss = storage.resolve_reference(ref)
    if not gloss:
        return
    logs = gloss.logs if isinstance(getattr(gloss, "logs", {}), dict) else {}
    logs[datetime.utcnow().isoformat() + "Z"] = SPLIT_LOG_MARKER
    gloss.logs = logs
    storage.save_gloss(gloss)


def judge_can_split(api_key: str, gloss_content: str, language: str, context: str) -> bool:
    try:
        from openai import OpenAI
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Install openai package: pip install openai") from exc
    client = OpenAI(api_key=api_key)
    prompt = (
        f"Decide if the {language} expression '{gloss_content}' can be reasonably split into learnable parts. "
        "Return JSON with boolean field 'can_split'."
    )
    if context:
        prompt += f" Context: {context}"
    resp = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[
            {"role": "system", "content": "You judge if expressions can be split into learnable parts."},
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


def split_parts(api_key: str, gloss_content: str, language: str, context: str) -> list[str]:
    try:
        from openai import OpenAI
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Install openai package: pip install openai") from exc
    client = OpenAI(api_key=api_key)
    prompt = (
        f"Take this {language} expression or phrase and break it up into parts that can be learned on their own. "
        "Return a JSON object with a 'parts' array of strings. Avoid repetition. "
        f"Expression: {gloss_content}"
    )
    if context:
        prompt += f" Context: {context}"
    resp = client.chat.completions.create(
        model=SPLIT_MODEL,
        messages=[
            {"role": "system", "content": "You are a concise linguistic decomposition assistant."},
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


def break_up_parts_flow(storage: GlossStorage, state: dict[str, Any]):
    api_key = ensure_api_key()
    if not api_key:
        message_dialog(title="Error", text="OPENAI_API_KEY required").run()
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

    gloss_choices = []
    for ref in refs:
        g = storage.resolve_reference(ref)
        gloss_choices.append((ref, f"{ref} — {g.content if g else '?'}"))

    selected_refs = checkboxlist_dialog(
        title="Select glosses to split",
        text="Select glosses lacking parts",
        values=gloss_choices,
    ).run()
    if not selected_refs:
        return

    ctx = input_dialog(title="Context", text="Extra context (optional):").run() or ""

    results = []
    for ref in selected_refs:
        gl = storage.resolve_reference(ref)
        if not gl:
            continue
        can_split = judge_can_split(api_key, gl.content, gl.language, ctx)
        if not can_split:
            mark_split_unnecessary(storage, ref)
            continue
        parts = split_parts(api_key, gl.content, gl.language, ctx)
        results.append((ref, gl.content, parts))

    accepted_total = 0
    for ref, content, parts in results:
        if not parts:
            continue
        selection = checkbox_dialog_default_checked(
            title=f"{ref}",
            text=f"{content}\nSelect parts to attach:",
            values=[(p, p) for p in parts],
            default_checked=parts,
        )
        if not selection:
            continue
        base = storage.resolve_reference(ref)
        if not base:
            continue
        for part_text in selection:
            part_gloss = storage.ensure_gloss(base.language, part_text)
            attach_relation(storage, base, "parts", part_gloss)
            accepted_total += 1

    message_dialog(title="Done", text=f"Added {accepted_total} parts.").run()

from __future__ import annotations

import json
import logging
from datetime import datetime

from prompt_toolkit.shortcuts import checkboxlist_dialog, message_dialog, ProgressBar

from src.shared.languages import get_ai_note
from src.shared.storage import GlossStorage, attach_relation
from src.shared.tree import collect_situation_stats, USAGE_IMPOSSIBLE_MARKER

logger = logging.getLogger(__name__)

# AI model/prompt constants
USAGE_MODEL = "gpt-4o-mini"
USAGE_SYSTEM_PROMPT = "You return concise usage examples for language learning."
USAGE_USER_PROMPT = (
    "Return three short, easily understandable, real, natural language examples that utilize the expression '{content}' "
    "in {language}. Each example should be a single sentence and practical for learners. "
    "Respond as JSON with an 'examples' array of strings."
)


def _openai_client(api_key: str):
    try:
        from openai import OpenAI
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Install openai package: pip install openai") from exc
    return OpenAI(api_key=api_key)


def generate_examples(api_key: str, gloss_content: str, language: str, ai_note: str = "", context: str = "") -> list[str]:
    client = _openai_client(api_key)
    prompt = USAGE_USER_PROMPT.format(content=gloss_content, language=language)
    if ai_note:
        prompt += f" Notes for this language: {ai_note}."
    if context:
        prompt += f" Additional context: {context}"
    resp = client.chat.completions.create(
        model=USAGE_MODEL,
        messages=[
            {"role": "system", "content": USAGE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=220,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "usage_examples",
                "schema": {
                    "type": "object",
                    "properties": {"examples": {"type": "array", "items": {"type": "string"}}},
                    "required": ["examples"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        },
    )
    content = resp.choices[0].message.content.strip()  # type: ignore[index]
    try:
        parsed = json.loads(content)
        examples = parsed.get("examples", []) if isinstance(parsed, dict) else []
    except Exception:
        examples = []
    return [ex.strip() for ex in examples if isinstance(ex, str) and ex.strip()]


def flow_add_usage_examples_ai(storage: GlossStorage, state: dict) -> None:
    api_key = (state.get("settings") or {}).get("OPENAI_API_KEY")
    if not api_key:
        message_dialog(title="Error", text="OPENAI_API_KEY required.").run()
        return
    situation = storage.resolve_reference(state["situation_ref"])
    if not situation:
        message_dialog(title="Error", text=f"Missing situation {state['situation_ref']}").run()
        return

    stats = collect_situation_stats(storage, situation, state["native_language"], state["target_language"])
    candidate_refs = list(stats.get("usage_missing", []))
    glosses = []
    for ref in candidate_refs:
        gl = storage.resolve_reference(ref)
        if gl and gl.language == state["target_language"]:
            glosses.append(gl)
    if not glosses:
        message_dialog(title="Info", text="No glosses need usage examples.").run()
        return

    values = [(f"{gl.language}:{gl.slug}", gl.content) for gl in glosses]
    selection = checkboxlist_dialog(
        title="Select glosses",
        text="Select glosses to generate usage examples for.\nUnselected will be marked impossible.",
        values=values,
        default_values=[val for val, _ in values],
    ).run()
    if selection is None:
        return

    selection_set = set(selection)
    # Mark unselected as impossible
    for ref, _label in values:
        if ref in selection_set:
            continue
        gl = storage.resolve_reference(ref)
        if not gl:
            continue
        logs = gl.logs if isinstance(getattr(gl, "logs", {}), dict) else {}
        logs[datetime.utcnow().isoformat() + "Z"] = f"{USAGE_IMPOSSIBLE_MARKER}:{state['target_language']}"
        gl.logs = logs
        storage.save_gloss(gl)

    targets = [storage.resolve_reference(ref) for ref in selection]
    targets = [gl for gl in targets if gl]
    if not targets:
        message_dialog(title="Info", text="No glosses selected.").run()
        return

    ai_note = get_ai_note(state["target_language"])
    results: list[tuple[str, str, list[str]]] = []
    with ProgressBar(title="Generating usage examples") as pb:
        for gl in pb(targets):
            try:
                examples = generate_examples(api_key, gl.content, gl.language, ai_note=ai_note)
            except Exception as exc:  # noqa: BLE001
                logger.error("Usage examples failed for %s: %s", gl.slug, exc)
                continue
            if examples:
                results.append((f"{gl.language}:{gl.slug}", gl.content, examples))

    if not results:
        message_dialog(title="Info", text="No examples generated.").run()
        return

    added = 0
    errors: list[str] = []
    for ref, content, examples in results:
        vals = [(ex, ex) for ex in examples]
        selection = checkboxlist_dialog(
            title=ref,
            text=f"{content}\nSelect examples to attach:",
            values=vals,
            default_values=[ex for ex, _ in vals],
        ).run()
        if not selection:
            continue
        base = storage.resolve_reference(ref)
        if not base:
            errors.append(f"{ref}: missing base gloss")
            continue
        for ex_text in selection:
            try:
                ex_gloss = storage.ensure_gloss(base.language, ex_text)
                attach_relation(storage, base, "usage_examples", ex_gloss)
                added += 1
            except Exception as exc:  # noqa: BLE001
                msg = f"{ref} :: '{ex_text}' -> {exc}"
                logger.error(msg)
                errors.append(msg)

    if errors:
        message_dialog(title="Done with errors", text=f"Added {added} examples.\nSee log for errors.").run()
    else:
        message_dialog(title="Done", text=f"Added {added} examples.").run()

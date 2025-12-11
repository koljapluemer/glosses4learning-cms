from __future__ import annotations

import json
import logging

from prompt_toolkit.shortcuts import checkboxlist_dialog, message_dialog, ProgressBar

from src.shared.languages import get_ai_note
from src.shared.storage import GlossStorage, attach_relation
from src.shared.tree import collect_situation_stats

logger = logging.getLogger(__name__)

# AI model/prompt constants
TRANSLATE_MODEL = "gpt-4o-mini"
TRANSLATE_SYSTEM_PROMPT = "You are a concise translation assistant for language learning glosses."
TRANSLATE_USER_PROMPT = (
    "Translate the following gloss into {target_language}. "
    "Return a JSON object with a 'translations' array of translation strings. Keep them concise. Gloss: {content}"
)


def _openai_client(api_key: str):
    try:
        from openai import OpenAI
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Install openai package: pip install openai") from exc
    return OpenAI(api_key=api_key)


def translate_gloss(api_key: str, content: str, target_language: str, ai_note: str = "", context: str = "") -> list[str]:
    client = _openai_client(api_key)
    prompt = TRANSLATE_USER_PROMPT.format(target_language=target_language, content=content)
    if ai_note:
        prompt += f" Notes for this language: {ai_note}."
    if context:
        prompt += f" Additional context: {context}"
    resp = client.chat.completions.create(
        model=TRANSLATE_MODEL,
        messages=[
            {"role": "system", "content": TRANSLATE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=200,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "translation_list",
                "schema": {
                    "type": "object",
                    "properties": {"translations": {"type": "array", "items": {"type": "string"}}},
                    "required": ["translations"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        },
    )
    content = resp.choices[0].message.content.strip()  # type: ignore[index]
    try:
        parsed = json.loads(content)
        translations = parsed.get("translations", []) if isinstance(parsed, dict) else []
    except Exception:
        translations = []
    return [t.strip() for t in translations if isinstance(t, str) and t.strip()]


def flow_translate_untranslated_native_ai(storage: GlossStorage, state: dict):
    """
    Translate target-language glosses that lack native-language translations.
    """
    api_key = (state.get("settings") or {}).get("OPENAI_API_KEY")
    if not api_key:
        message_dialog(title="Error", text="OPENAI_API_KEY required.").run()
        return
    situation = storage.resolve_reference(state["situation_ref"])
    if not situation:
        message_dialog(title="Error", text=f"Missing situation {state['situation_ref']}").run()
        return

    stats = collect_situation_stats(storage, situation, state["native_language"], state["target_language"])
    candidate_refs = list(stats.get("native_missing", []))
    glosses = []
    for ref in candidate_refs:
        gl = storage.resolve_reference(ref)
        if gl and gl.language == state["target_language"]:
            glosses.append(gl)
    if not glosses:
        message_dialog(title="Info", text="No target glosses need native translations.").run()
        return

    ai_note = get_ai_note(state["native_language"])
    results: list[tuple[str, str, list[str]]] = []
    with ProgressBar(title="Translating to native language") as pb:
        for gl in pb(glosses):
            try:
                translations = translate_gloss(api_key, gl.content, state["native_language"], ai_note=ai_note)
            except Exception as exc:  # noqa: BLE001
                logger.error("Translation failed for %s: %s", gl.slug, exc)
                continue
            if translations:
                results.append((f"{gl.language}:{gl.slug}", gl.content, translations))

    if not results:
        message_dialog(title="Info", text="No translations generated.").run()
        return

    added = 0
    errors: list[str] = []
    for ref, content, translations in results:
        vals = [(t, t) for t in translations]
        selection = checkboxlist_dialog(
            title=ref,
            text=f"{content}\nSelect translations to attach (target language: {state['native_language']}):",
            values=vals,
            default_values=[t for t, _ in vals],
        ).run()
        if not selection:
            continue
        base = storage.resolve_reference(ref)
        if not base:
            errors.append(f"{ref}: missing base gloss")
            continue
        for t_text in selection:
            try:
                t_gloss = storage.ensure_gloss(state["native_language"], t_text)
                attach_relation(storage, base, "translations", t_gloss)
                attach_relation(storage, t_gloss, "translations", base)
                added += 1
            except Exception as exc:  # noqa: BLE001
                msg = f"{ref} :: '{t_text}' -> {exc}"
                logger.error(msg)
                errors.append(msg)

    if errors:
        message_dialog(title="Done with errors", text=f"Added {added} translations.\nSee log for errors.").run()
    else:
        message_dialog(title="Done", text=f"Added {added} translations.").run()

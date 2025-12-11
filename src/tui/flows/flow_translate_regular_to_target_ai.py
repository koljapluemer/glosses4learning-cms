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
REGULAR_SYSTEM_PROMPT = """You are a precise translation assistant for language learning glosses.

Your task:
- Provide accurate, concise translations of words and phrases
- Focus on the most common translations first
- Include usage notes ONLY when there are important contextual differences
- Keep translations natural and idiomatic
"""

REGULAR_USER_PROMPT = """Translate this into {target_language}: "{content}"
{ai_note_text}

Provide 2-3 common translations. Include usage notes ONLY when translations have different contexts or registers.

Return JSON with translations array. Each item:
- "text": the translation (REQUIRED)
- "note": usage guidance in {native_language} ONLY if needed, e.g., "formal", "casual", "written only" (OPTIONAL)
"""


def _openai_client(api_key: str):
    try:
        from openai import OpenAI
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Install openai package: pip install openai") from exc
    return OpenAI(api_key=api_key)


def translate_gloss(
    api_key: str, content: str, target_language: str, native_language: str, ai_note: str = ""
) -> list[dict]:
    """
    Translate a regular gloss.

    Returns:
        List of dicts with 'text' (required) and 'note' (optional) keys
    """
    client = _openai_client(api_key)
    ai_note_text = f"Notes for this language: {ai_note}." if ai_note else ""
    prompt = REGULAR_USER_PROMPT.format(
        content=content,
        target_language=target_language,
        native_language=native_language,
        ai_note_text=ai_note_text,
    )
    resp = client.chat.completions.create(
        model=TRANSLATE_MODEL,
        messages=[
            {"role": "system", "content": REGULAR_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=200,
        response_format={
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
        },
    )
    content_str = resp.choices[0].message.content.strip()  # type: ignore[index]
    try:
        parsed = json.loads(content_str)
        translations = parsed.get("translations", []) if isinstance(parsed, dict) else []
    except Exception:
        translations = []
    # Validate and clean
    result = []
    for item in translations:
        if isinstance(item, dict) and isinstance(item.get("text"), str) and item["text"].strip():
            result.append(item)
    return result


def attach_translation_with_note(
    storage: GlossStorage,
    native_gloss,
    translation_text: str,
    target_language: str,
    note_text: str | None,
    native_language: str,
) -> None:
    """
    Attach translation to native gloss with optional note.

    Args:
        storage: GlossStorage instance
        native_gloss: Source gloss in native language
        translation_text: Translation text
        target_language: Target language code
        note_text: Optional note in native language
        native_language: Native language code
    """
    # Create translation gloss in target language
    translation_gloss = storage.ensure_gloss(target_language, translation_text)

    # Bidirectional translation relation
    attach_relation(storage, native_gloss, "translations", translation_gloss)
    attach_relation(storage, translation_gloss, "translations", native_gloss)

    # One-way note relation (if note exists)
    # Note is in native language, attached TO the target translation
    if note_text and note_text.strip():
        note_gloss = storage.ensure_gloss(native_language, note_text.strip())
        attach_relation(storage, translation_gloss, "notes", note_gloss)


def flow_translate_regular_to_target_ai(storage: GlossStorage, state: dict):
    """
    Translate regular native-language glosses to target language.
    Excludes glosses tagged with 'eng:paraphrase'.
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
    candidate_refs = list(stats.get("target_missing", []))
    glosses = []
    for ref in candidate_refs:
        gl = storage.resolve_reference(ref)
        if gl and gl.language == state["native_language"]:
            # Filter: EXCLUDE paraphrases
            if "eng:paraphrase" not in (gl.tags or []):
                glosses.append(gl)
    if not glosses:
        message_dialog(title="Info", text="No regular native glosses need target translations.").run()
        return

    ai_note = get_ai_note(state["target_language"])
    results: list[tuple[str, str, list[dict]]] = []
    with ProgressBar(title="Translating regular glosses to target language") as pb:
        for gl in pb(glosses):
            try:
                translations = translate_gloss(
                    api_key, gl.content, state["target_language"], state["native_language"], ai_note=ai_note
                )
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
    for ref, content, translations_data in results:
        vals = []
        for trans_data in translations_data:
            text = trans_data.get("text", "")
            note = trans_data.get("note", "")
            # Show note in checkbox label for context
            label = f"{text}" + (f" [{note}]" if note else "")
            vals.append((trans_data, label))

        selection = checkboxlist_dialog(
            title=ref,
            text=f"{content}\nSelect translations to attach (target language: {state['target_language']}):",
            values=vals,
            default_values=[data for data, _ in vals],
        ).run()
        if not selection:
            continue
        native_gloss = storage.resolve_reference(ref)
        if not native_gloss:
            errors.append(f"{ref}: missing base gloss")
            continue
        for trans_data in selection:
            text = trans_data.get("text", "").strip()
            note = trans_data.get("note", "").strip() if trans_data.get("note") else None
            try:
                attach_translation_with_note(
                    storage, native_gloss, text, state["target_language"], note, state["native_language"]
                )
                added += 1
            except Exception as exc:  # noqa: BLE001
                msg = f"{ref} :: '{text}' -> {exc}"
                logger.error(msg)
                errors.append(msg)

    if errors:
        message_dialog(title="Done with errors", text=f"Added {added} translations.\nSee log for errors.").run()
    else:
        message_dialog(title="Done", text=f"Added {added} translations.").run()

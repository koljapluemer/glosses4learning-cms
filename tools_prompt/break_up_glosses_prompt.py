from __future__ import annotations

"""
Prompt-toolkit PoC: split glosses (parts missing) for a situation.

Flow:
1) Pick situation, native language, target language.
2) Enter OpenAI API key, model, extra context.
3) Select which glosses to split (from parts_missing stats).
4) Run AI generation for selected glosses.
5) For each gloss, select which parts to accept; write back to data.
"""

import os
import sys
from pathlib import Path
from typing import List

from prompt_toolkit.shortcuts import checkboxlist_dialog, input_dialog, message_dialog, radiolist_dialog

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools_tk.shared.gloss_storage import GlossStorage, attach_relation  # reuse storage
from tools_tk.shared.situations_tree import collect_situation_stats  # reuse stats


DATA_ROOT = REPO_ROOT / "data"


def generate_parts(api_key: str, model: str, gloss_content: str, language: str, context: str = "") -> List[str]:
    """Call OpenAI to generate parts for a gloss."""
    try:
        from openai import OpenAI
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Install openai package: pip install openai") from exc

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required.")

    client = OpenAI(api_key=api_key)
    prompt = (
        f"Take this {language} expression or phrase and break it up into parts that can be learned on their own. "
        "Return a JSON object with a 'parts' array of strings. Avoid repetition. "
        f"Expression: {gloss_content}"
    )
    if context:
        prompt += f" Context: {context}"

    resp = client.chat.completions.create(
        model=model or "gpt-4o-mini",
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
    import json

    try:
        parsed = json.loads(content)
        parts = parsed.get("parts", []) if isinstance(parsed, dict) else []
    except Exception:
        parts = []
    return [p.strip() for p in parts if isinstance(p, str) and p.strip()]


def pick_situation(storage: GlossStorage):
    glosses = storage.list_glosses()
    situations = [g for g in glosses if "eng:situation" in (g.tags or [])]
    situation_opts = [(f"{g.content} [{g.language}:{g.slug}]", f"{g.language}:{g.slug}") for g in situations]
    if not situation_opts:
        message_dialog(title="Error", text="No situations found.").run()
        sys.exit(1)
    selected = radiolist_dialog(
        title="Select situation",
        text="Choose a situation to process.",
        values=[(val, label) for label, val in situation_opts],
    ).run()
    return selected


def pick_language(title: str, languages: list[str]):
    selected = radiolist_dialog(
        title=title,
        text=title,
        values=[(lang, lang) for lang in languages],
    ).run()
    return selected


def pick_api_key(default: str = ""):
    api_key = input_dialog(title="OpenAI API key", text="Enter OPENAI_API_KEY:", password=True).run()
    return api_key or default


def main():
    storage = GlossStorage(DATA_ROOT)
    glosses = storage.list_glosses()
    lang_codes = sorted({g.language for g in glosses})

    situation_ref = pick_situation(storage)
    if not situation_ref:
        return

    target_language = pick_language("Select target language", lang_codes)
    native_language = pick_language("Select native language", lang_codes)
    if not target_language or not native_language:
        return

    api_key = pick_api_key(os.getenv("OPENAI_API_KEY", ""))
    if not api_key:
        message_dialog(title="Error", text="OPENAI_API_KEY is required.").run()
        return

    model = input_dialog(title="Model", text="Model (default gpt-4o-mini):").run() or "gpt-4o-mini"
    context = input_dialog(title="Context", text="Extra context (optional):").run() or ""

    situation = storage.resolve_reference(situation_ref)
    if not situation:
        message_dialog(title="Error", text=f"Missing situation {situation_ref}").run()
        return

    stats = collect_situation_stats(storage, situation, native_language, target_language)
    refs = list(stats.get("parts_missing", []))
    if not refs:
        message_dialog(title="Info", text="No glosses need splitting (parts_missing empty).").run()
        return

    gloss_choices = []
    for ref in refs:
        g = storage.resolve_reference(ref)
        gloss_choices.append((ref, f"{ref} — {g.content if g else '?'}"))

    selected_refs = checkboxlist_dialog(
        title="Select glosses to split",
        text="Select glosses lacking parts",
        values=[(ref, label) for ref, label in gloss_choices],
    ).run()
    if not selected_refs:
        return

    results = []
    for ref in selected_refs:
        g = storage.resolve_reference(ref)
        if not g:
            continue
        parts = generate_parts(api_key, model, g.content, g.language, context)
        results.append((ref, g.content, parts))

    accepted_total = 0
    for ref, content, parts in results:
        if not parts:
            continue
        selection = checkboxlist_dialog(
            title=f"Accept parts for {ref}",
            text=f"{content}\nSelect parts to attach:",
            values=[(p, p) for p in parts],
        ).run()
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


if __name__ == "__main__":
    main()

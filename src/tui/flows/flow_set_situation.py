from __future__ import annotations

from prompt_toolkit.shortcuts import choice, message_dialog

from src.shared.storage import GlossStorage


def set_situation_flow(storage: GlossStorage, state: dict) -> dict | None:
    glosses = storage.list_glosses()
    situations = [g for g in glosses if "eng:situation" in (g.tags or [])]
    if not situations:
        message_dialog(title="Error", text="No situations found.").run()
        return None
    situation_opts = [(f"{g.language}:{g.slug}", f"{g.content} [{g.language}:{g.slug}]") for g in situations]
    situation_ref = choice(
        message="Select situation",
        options=situation_opts,
        default=situation_opts[0][0] if situation_opts else None,
    )
    langs = sorted({g.language for g in glosses})
    native_language = choice(
        message="Select native language",
        options=[(l, l) for l in langs],
        default=state.get("native_language") or (langs[0] if langs else None),
    )
    target_language = choice(
        message="Select target language",
        options=[(l, l) for l in langs],
        default=state.get("target_language") or (langs[0] if langs else None),
    )
    if not (situation_ref and native_language and target_language):
        return None
    return {
        "situation_ref": situation_ref,
        "native_language": native_language,
        "target_language": target_language,
    }

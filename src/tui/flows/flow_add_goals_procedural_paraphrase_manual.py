from __future__ import annotations

import logging
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit
from prompt_toolkit.shortcuts import message_dialog
from prompt_toolkit.widgets import TextArea, Dialog, Button, Label

from src.shared.storage import Gloss, GlossStorage, attach_relation

logger = logging.getLogger(__name__)


def _textarea_dialog(title: str, text: str) -> str | None:
    textarea = TextArea(height=10, multiline=True)
    result = {"value": None}

    def accept():
        result["value"] = textarea.text
        app.exit()

    def cancel():
        result["value"] = None
        app.exit()

    dialog = Dialog(
        title=title,
        body=HSplit([Label(text=text), textarea]),
        buttons=[Button(text="OK", handler=accept), Button(text="Cancel", handler=cancel)],
        with_background=True,
    )
    kb = KeyBindings()

    @kb.add("escape")
    def _(_):
        cancel()

    app = Application(layout=Layout(dialog), key_bindings=kb, mouse_support=True, full_screen=True)
    app.run()
    return result["value"]


def flow_add_goals_procedural_paraphrase_manual(storage: GlossStorage, state: dict) -> None:
    """
    Manual entry of understand-expression goals in target language (one per line).
    Tags: eng:understand-expression-goal
    """
    target_language = state["target_language"]
    situation_ref = state["situation_ref"]
    situation = storage.resolve_reference(situation_ref)
    if not situation:
        message_dialog(title="Error", text=f"Missing situation {situation_ref}").run()
        return

    text = _textarea_dialog(
        title="Add procedural paraphrase goals (manual)",
        text=f"Enter one target-language expression per line (language: {target_language}):",
    )
    if not text:
        return
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        message_dialog(title="Info", text="No expressions provided.").run()
        return

    created = 0
    skipped = 0
    for content in lines:
        existing = storage.find_gloss_by_content(target_language, content)
        if existing:
            tags = existing.tags or []
            if "eng:understand-expression-goal" not in tags:
                existing.tags = tags + ["eng:understand-expression-goal"]
                storage.save_gloss(existing)
                created += 1
            else:
                skipped += 1
            goal = existing
        else:
            goal = storage.create_gloss(
                Gloss(content=content, language=target_language, tags=["eng:understand-expression-goal"])
            )
            created += 1
        attach_relation(storage, situation, "children", goal)

    logger.info("Procedural paraphrase goals manual: created=%s skipped=%s", created, skipped)
    message_dialog(title="Done", text=f"Created {created}, skipped {skipped}.").run()

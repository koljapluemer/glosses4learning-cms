from __future__ import annotations

import logging
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit
from prompt_toolkit.shortcuts import message_dialog
from prompt_toolkit.widgets import TextArea, Dialog, Button, Label

from src.shared.storage import Gloss, GlossStorage

logger = logging.getLogger(__name__)

# Situations are stored in English with the eng:situation tag
SITUATION_LANGUAGE = "eng"
SITUATION_TAG = "eng:situation"


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


def flow_add_situations_manual(storage: GlossStorage, state: dict) -> None:
    """
    Add situations manually (one per line, stored as English glosses tagged eng:situation).
    """
    text = _textarea_dialog(
        title="Add situations (manual)",
        text="Enter one situation title per line (language: eng).",
    )
    if not text:
        return

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        message_dialog(title="Info", text="No situations provided.").run()
        return

    created = 0
    updated = 0
    for content in lines:
        existing = storage.find_gloss_by_content(SITUATION_LANGUAGE, content)
        if existing:
            tags = existing.tags or []
            if SITUATION_TAG not in tags:
                existing.tags = tags + [SITUATION_TAG]
                storage.save_gloss(existing)
                updated += 1
            continue
        storage.create_gloss(Gloss(content=content, language=SITUATION_LANGUAGE, tags=[SITUATION_TAG]))
        created += 1

    logger.info("Situations manual: created=%s updated=%s", created, updated)
    message_dialog(title="Done", text=f"Created {created}, updated {updated}.").run()

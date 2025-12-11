from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit
from prompt_toolkit.widgets import Button, CheckboxList, Dialog, Label


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def iso_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def checkbox_dialog_default_checked(title: str, text: str, values: list[tuple[str, str]], default_checked: list[str]):
    """
    Checkbox dialog with default selections.
    values: list of (value, label)
    default_checked: list of values that should start checked.
    Returns list of selected values or None if cancelled.
    """
    checkbox = CheckboxList(values=values)
    checkbox.current_values = list(default_checked)

    result: list | None = None

    def accept():
        nonlocal result
        result = list(checkbox.current_values)
        app.exit()

    def cancel():
        nonlocal result
        result = None
        app.exit()

    dialog = Dialog(
        title=title,
        body=HSplit([Label(text=text), checkbox]),
        buttons=[Button(text="OK", handler=accept), Button(text="Cancel", handler=cancel)],
        width=None,
        with_background=True,
    )

    kb = KeyBindings()

    @kb.add("escape")
    def _(_):
        cancel()

    app = Application(layout=Layout(dialog), key_bindings=kb, mouse_support=True, full_screen=False)
    app.run()
    return result

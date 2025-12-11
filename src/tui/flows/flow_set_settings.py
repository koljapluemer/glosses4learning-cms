from __future__ import annotations

from prompt_toolkit.shortcuts import input_dialog, message_dialog


def settings_flow(settings: dict) -> str | None:
    key = settings.get("OPENAI_API_KEY", "")
    new_key = input_dialog(title="Settings", text="Enter OPENAI_API_KEY:", default=key, password=True).run()
    if not new_key:
        message_dialog(title="Error", text="OPENAI_API_KEY is required.").run()
        return None
    return new_key

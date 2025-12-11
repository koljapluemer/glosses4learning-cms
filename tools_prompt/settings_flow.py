from __future__ import annotations

from pathlib import Path

from prompt_toolkit.shortcuts import input_dialog, message_dialog

from tools_prompt.common import load_json, save_json


SETTINGS_FILE = Path(__file__).resolve().parent / "settings.json"


def get_api_key() -> str:
    settings = load_json(SETTINGS_FILE)
    return settings.get("OPENAI_API_KEY", "")


def settings_flow() -> str | None:
    key = input_dialog(title="Settings", text="Enter OPENAI_API_KEY:", password=True).run()
    if key:
        save_json(SETTINGS_FILE, {"OPENAI_API_KEY": key})
        return key
    message_dialog(title="Error", text="OPENAI_API_KEY is required.").run()
    return None


def ensure_api_key() -> str | None:
    from os import getenv

    env_key = getenv("OPENAI_API_KEY")
    if env_key:
        return env_key
    key = get_api_key()
    if key:
        return key
    return settings_flow()

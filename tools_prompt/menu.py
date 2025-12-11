from __future__ import annotations

from prompt_toolkit.shortcuts import choice, message_dialog

from tools_prompt.break_up_parts_flow import break_up_parts_flow
from tools_prompt.settings_flow import ensure_api_key, settings_flow
from tools_prompt.state_flow import load_state, save_state, set_situation_flow
from tools_prompt.tree_view_flow import tree_view_flow
from tools_tk.shared.gloss_storage import GlossStorage


def ensure_context(storage: GlossStorage):
    if not ensure_api_key():
        return None
    state = load_state()
    if not state.get("situation_ref") or not state.get("native_language") or not state.get("target_language"):
        state = set_situation_flow(storage)
    return state


def main_menu(storage: GlossStorage):
    while True:
        state = ensure_context(storage)
        if not state:
            return
        title = f"Menu — Situation: {state['situation_ref']} | Native: {state['native_language']} | Target: {state['target_language']}"
        selection = choice(
            message=title,
            options=[
                ("tree", "View situation tree"),
                ("break", "Automatically break up glosses into parts"),
                ("set_situation", "Change situation / languages"),
                ("settings", "Settings (API key)"),
                ("quit", "Quit"),
                ("exit", "Exit program"),
            ],
            default="break",
        )
        if selection == "tree":
            tree_view_flow(storage, state)
        elif selection == "break":
            break_up_parts_flow(storage, state)
        elif selection == "set_situation":
            state = set_situation_flow(storage) or {}
            save_state(state)
        elif selection == "settings":
            settings_flow()
        elif selection == "quit":
            return
        elif selection == "exit":
            # Return a sentinel to end the whole program.
            return "exit"
        else:
            message_dialog(title="Info", text="No action selected.").run()

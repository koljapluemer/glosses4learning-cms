from __future__ import annotations

from prompt_toolkit.shortcuts import message_dialog, radiolist_dialog

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
        choice = radiolist_dialog(
            title=title,
            text="Select an action",
            values=[
                ("tree", "View situation tree"),
                ("break", "Automatically break up glosses into parts"),
                ("set_situation", "Change situation / languages"),
                ("settings", "Settings (API key)"),
                ("quit", "Quit"),
            ],
        ).run()
        if choice == "tree":
            tree_view_flow(storage, state)
        elif choice == "break":
            break_up_parts_flow(storage, state)
        elif choice == "set_situation":
            state = set_situation_flow(storage) or {}
            save_state(state)
        elif choice == "settings":
            settings_flow()
        elif choice == "quit":
            return
        else:
            message_dialog(title="Info", text="No action selected.").run()

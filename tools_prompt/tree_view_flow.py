from __future__ import annotations

from prompt_toolkit.shortcuts import message_dialog

from tools_tk.shared.gloss_storage import GlossStorage
from tools_tk.shared.situations_tree import build_goal_nodes, render_tree_text


def tree_view_flow(storage: GlossStorage, state: dict):
    situation = storage.resolve_reference(state["situation_ref"])
    if not situation:
        message_dialog(title="Error", text=f"Missing situation {state['situation_ref']}").run()
        return
    nodes, _ = build_goal_nodes(
        situation,
        storage=storage,
        native_language=state["native_language"],
        target_language=state["target_language"],
    )
    text = render_tree_text(nodes) or "(no tree)"
    message_dialog(
        title="Situation Tree",
        text=f"{situation.content} [{state['native_language']} -> {state['target_language']}]\n\n{text}",
    ).run()

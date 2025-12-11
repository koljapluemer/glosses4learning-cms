from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from prompt_toolkit.shortcuts import choice, message_dialog

from src.shared.log import configure_logging
from src.shared.state import load_state, save_state
from src.shared.storage import GlossStorage
from src.tui.flows.flow_add_goals_expression_ai import flow_add_goals_expression_ai
from src.tui.flows.flow_add_goals_expression_manual import flow_add_goals_expression_manual
from src.tui.flows.flow_add_goals_procedural_paraphrase_ai import flow_add_goals_procedural_paraphrase_ai
from src.tui.flows.flow_add_goals_procedural_paraphrase_manual import flow_add_goals_procedural_paraphrase_manual
from src.tui.flows.flow_add_situations_ai import flow_add_situations_ai
from src.tui.flows.flow_add_situations_manual import flow_add_situations_manual
from src.tui.flows.flow_add_usage_examples_ai import flow_add_usage_examples_ai
from src.tui.flows.flow_set_settings import settings_flow
from src.tui.flows.flow_set_situation import set_situation_flow
from src.tui.flows.flow_split_glosses_of_situation_into_parts_ai import (
    flow_split_glosses_of_situation_into_parts_ai,
)
from src.tui.flows.flow_export_situations_batch import flow_export_situations_batch
from src.tui.flows.flow_translate_untranslated_native_ai import flow_translate_untranslated_native_ai
from src.tui.flows.flow_translate_untranslated_target_ai import flow_translate_untranslated_target_ai


def ensure_context(storage: GlossStorage):
    state = load_state()
    if not state.get("settings") or not state["settings"].get("OPENAI_API_KEY"):
        key = settings_flow(state.get("settings") or {})
        if not key:
            return None
        state.setdefault("settings", {})["OPENAI_API_KEY"] = key
        save_state(state)
    if not state.get("situation_ref") or not state.get("native_language") or not state.get("target_language"):
        new_state = set_situation_flow(storage, state)
        if not new_state:
            return None
        state.update(new_state)
        save_state(state)
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
                ("add_situation_ai", "Add situations (AI)"),
                ("add_situation_manual", "Add situations (manual)"),
                ("add_expr_ai", "Add expression goals (AI, native language)"),
                ("add_expr_manual", "Add expression goals (manual, native language)"),
                ("add_understand_ai", "Add understand goals (AI, target language)"),
                ("add_understand_manual", "Add understand goals (manual, target language)"),
                ("add_usage_ai", "Add usage examples (AI, target language)"),
                ("translate_native", "Translate target glosses to native (AI)"),
                ("translate_target", "Translate native glosses to target (AI)"),
                ("split_parts", "Split glosses into parts (AI)"),
                ("batch_export", "Batch export situations"),
                ("set_situation", "Change situation / languages"),
                ("settings", "Settings (API key)"),
                ("quit", "Quit"),
            ],
            default="quit",
        )
        if selection == "add_situation_ai":
            flow_add_situations_ai(storage, state)
        elif selection == "add_situation_manual":
            flow_add_situations_manual(storage, state)
        elif selection == "add_expr_ai":
            flow_add_goals_expression_ai(storage, state)
        elif selection == "add_expr_manual":
            flow_add_goals_expression_manual(storage, state)
        elif selection == "add_understand_ai":
            flow_add_goals_procedural_paraphrase_ai(storage, state)
        elif selection == "add_understand_manual":
            flow_add_goals_procedural_paraphrase_manual(storage, state)
        elif selection == "add_usage_ai":
            flow_add_usage_examples_ai(storage, state)
        elif selection == "translate_native":
            flow_translate_untranslated_native_ai(storage, state)
        elif selection == "translate_target":
            flow_translate_untranslated_target_ai(storage, state)
        elif selection == "split_parts":
            flow_split_glosses_of_situation_into_parts_ai(storage, state)
        elif selection == "batch_export":
            flow_export_situations_batch(storage, state)
        elif selection == "set_situation":
            new_state = set_situation_flow(storage, state)
            if new_state:
                state.update(new_state)
                save_state(state)
        elif selection == "settings":
            key = settings_flow(state.get("settings") or {})
            if key:
                state.setdefault("settings", {})["OPENAI_API_KEY"] = key
                save_state(state)
        elif selection == "quit":
            return
        else:
            message_dialog(title="Info", text="No action selected.").run()


def main():
    configure_logging()
    storage = GlossStorage(REPO_ROOT / "data")
    main_menu(storage)


if __name__ == "__main__":
    main()

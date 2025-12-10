from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from pathlib import Path
import sys

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools_tk.shared.gloss_storage import GlossStorage
from tools_tk.shared.situations_tree import build_goal_nodes, render_tree_text
from tools_tk.shared.state_store import load_state, save_state
from tools_tk.shared.tk_common import make_root, labeled_dropdown, readonly_text, set_text, status_label, update_status, on_close, button_row

DATA_ROOT = REPO_ROOT / "data"
STATE_DIR = Path(__file__).resolve().parents[1] / "shared"


def load_choices(storage: GlossStorage):
    glosses = storage.list_glosses()
    situations = [g for g in glosses if "eng:situation" in (g.tags or [])]
    situation_opts = [(f"{g.content} [{g.language}:{g.slug}]", f"{g.language}:{g.slug}") for g in situations]
    lang_codes = sorted({g.language for g in glosses})
    lang_opts = [(code, code) for code in lang_codes]
    return situation_opts, lang_opts


def main():
    storage = GlossStorage(DATA_ROOT)
    situation_opts, lang_opts = load_choices(storage)
    state = load_state(STATE_DIR)

    root = make_root("Situation Tree Viewer")

    header = ttk.Label(root, text="View situation tree and missing items", font=("TkDefaultFont", 12, "bold"))
    header.pack(pady=6)

    form = ttk.Frame(root)
    form.pack(fill=tk.X, padx=10, pady=4)

    sit_frame, sit_var = labeled_dropdown(form, "Situation", situation_opts, state.get("situation_ref"))
    nat_frame, nat_var = labeled_dropdown(form, "Native language", lang_opts, state.get("native_language"))
    tgt_frame, tgt_var = labeled_dropdown(form, "Target language", lang_opts, state.get("target_language"))
    sit_frame.pack(fill=tk.X, pady=2)
    nat_frame.pack(fill=tk.X, pady=2)
    tgt_frame.pack(fill=tk.X, pady=2)

    status = status_label(root)
    status.pack(pady=4)

    tree_box = readonly_text(root)
    tree_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    stats_box = readonly_text(root)
    stats_box.pack(fill=tk.X, padx=10, pady=4)

    def refresh():
        selection = {
            "situation_ref": sit_var.get(),
            "native_language": nat_var.get(),
            "target_language": tgt_var.get(),
        }
        if not selection["situation_ref"] or not selection["native_language"] or not selection["target_language"]:
            update_status(status, "Select situation + native + target languages", error=True)
            return
        situation = storage.resolve_reference(selection["situation_ref"])
        if not situation:
            update_status(status, f"Missing situation {selection['situation_ref']}", error=True)
            return
        nodes, stats = build_goal_nodes(
            situation,
            storage=storage,
            native_language=selection["native_language"],
            target_language=selection["target_language"],
        )
        tree_text = render_tree_text(nodes)
        set_text(tree_box, tree_text or "(no tree)")
        summary = {
            "parts_missing": len(stats.get("parts_missing", [])),
            "native_missing": len(stats.get("native_missing", [])),
            "target_missing": len(stats.get("target_missing", [])),
            "usage_missing": len(stats.get("usage_missing", [])),
            "glosses_to_learn": len(stats.get("glosses_to_learn", [])),
        }
        set_text(stats_box, str(summary))
        update_status(status, "Refreshed")
        save_state(STATE_DIR, selection)

    refresh_btn = ttk.Button(root, text="Refresh tree", command=refresh)
    button_row(root, refresh_btn).pack(pady=4)

    on_close(root, lambda: save_state(STATE_DIR, {
        "situation_ref": sit_var.get(),
        "native_language": nat_var.get(),
        "target_language": tgt_var.get(),
    }))

    refresh()
    root.mainloop()


if __name__ == "__main__":
    main()

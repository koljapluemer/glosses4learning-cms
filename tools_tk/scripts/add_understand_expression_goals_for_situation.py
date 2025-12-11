from __future__ import annotations

import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools_tk.shared.ai_calls import generate_understand_goals
from tools_tk.shared.gloss_storage import GlossStorage, attach_relation
from tools_tk.shared.state_store import load_state, save_state
from tools_tk.shared.tk_common import (
    button_row,
    labeled_dropdown,
    make_root,
    on_close,
    status_label,
    update_status,
)


DATA_ROOT = REPO_ROOT / "data"
STATE_DIR = HERE.parents[1] / "shared"


def load_choices(storage: GlossStorage):
    glosses = storage.list_glosses()
    situations = [g for g in glosses if "eng:situation" in (g.tags or [])]
    situation_opts = [(f"{g.content} [{g.language}:{g.slug}]", f"{g.language}:{g.slug}") for g in situations]
    lang_codes = sorted({g.language for g in glosses})
    lang_opts = [(code, code) for code in lang_codes]
    return situation_opts, lang_opts


def apply_understand_goals(storage: GlossStorage, situation_ref: str, target_language: str, goals: list[str]):
    situation = storage.resolve_reference(situation_ref)
    if not situation:
        raise ValueError(f"Missing situation {situation_ref}")
    created = 0
    skipped = 0
    for goal_text in goals:
        goal_text = goal_text.strip()
        if not goal_text:
            continue
        existing = storage.find_gloss_by_content(target_language, goal_text)
        if existing:
            tags = existing.tags or []
            if "eng:understand-expression-goal" not in tags:
                existing.tags = tags + ["eng:understand-expression-goal"]
                storage.save_gloss(existing)
                created += 1
            else:
                skipped += 1
            goal_gloss = existing
        else:
            from tools_tk.shared.gloss_storage import Gloss

            goal_gloss = storage.create_gloss(
                Gloss(content=goal_text, language=target_language, tags=["eng:understand-expression-goal"])
            )
            created += 1
        attach_relation(storage, situation, "children", goal_gloss)
    return created, skipped


def main():
    storage = GlossStorage(DATA_ROOT)
    situation_opts, lang_opts = load_choices(storage)
    state = load_state(STATE_DIR)

    root = make_root("Add understand-expression goals to situation")
    header = ttk.Label(root, text="Add understand-expression goals (target language)", font=("TkDefaultFont", 12, "bold"))
    header.pack(pady=6)

    form = ttk.Frame(root)
    form.pack(fill=tk.X, padx=10, pady=4)

    sit_frame, sit_var = labeled_dropdown(form, "Situation", situation_opts, state.get("situation_ref"))
    nat_frame, nat_var = labeled_dropdown(form, "Native language", lang_opts, state.get("native_language"))
    tgt_frame, tgt_var = labeled_dropdown(form, "Target language", lang_opts, state.get("target_language"))
    sit_frame.pack(fill=tk.X, pady=2)
    nat_frame.pack(fill=tk.X, pady=2)
    tgt_frame.pack(fill=tk.X, pady=2)

    model_label = ttk.Label(form, text="Model")
    model_label.pack(anchor=tk.W, pady=(8, 0))
    model_entry = ttk.Entry(form)
    model_entry.insert(0, "gpt-4o-mini")
    model_entry.pack(fill=tk.X)

    num_label = ttk.Label(form, text="# goals (1-10)")
    num_label.pack(anchor=tk.W, pady=(8, 0))
    num_spin = ttk.Spinbox(form, from_=1, to=10)
    num_spin.set("5")
    num_spin.pack(fill=tk.X)

    ctx_label = ttk.Label(form, text="Context (optional)")
    ctx_label.pack(anchor=tk.W, pady=(8, 0))
    ctx_text = tk.Text(form, height=3)
    ctx_text.pack(fill=tk.X)

    status = status_label(root)
    status.pack(pady=4)

    # Action buttons near the top
    btn_generate = ttk.Button(root, text="Generate")
    btn_accept_sel = ttk.Button(root, text="Accept selected")
    btn_accept_all = ttk.Button(root, text="Accept all")
    action_row = button_row(root, btn_generate, btn_accept_sel, btn_accept_all)
    action_row.pack(pady=6)

    # Results list with scrollbar (fixed height)
    results_label = ttk.Label(root, text="Generated goals (select to accept):")
    results_label.pack(anchor=tk.W, padx=10)
    results_frame = ttk.Frame(root)
    results_frame.pack(fill=tk.X, expand=False, padx=10, pady=6)
    results_scroll = ttk.Scrollbar(results_frame, orient=tk.VERTICAL)
    results_list = tk.Listbox(results_frame, selectmode=tk.MULTIPLE, height=10, yscrollcommand=results_scroll.set)
    results_scroll.config(command=results_list.yview)
    results_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    results_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def on_generate():
        results_list.delete(0, tk.END)
        if not sit_var.get() or not tgt_var.get():
            update_status(status, "Select situation and target language", error=True)
            return
        try:
            num = max(1, min(10, int(num_spin.get())))
        except Exception:
            num = 5
        situation = storage.resolve_reference(sit_var.get())
        if not situation:
            update_status(status, f"Missing situation {sit_var.get()}", error=True)
            return
        goals, error = generate_understand_goals(
            situation_content=situation.content,
            target_language=tgt_var.get(),
            num_goals=num,
            context=ctx_text.get("1.0", tk.END).strip(),
            model=model_entry.get().strip() or "gpt-4o-mini",
        )
        if error:
            update_status(status, f"Error: {error}", error=True)
            return
        if not goals:
            update_status(status, "No goals generated", error=True)
            return
        for g in goals:
            results_list.insert(tk.END, g)
        update_status(status, f"Generated {len(goals)} goals")

    def on_accept(selected_only: bool):
        if not sit_var.get() or not tgt_var.get():
            update_status(status, "Select situation and target language", error=True)
            return
        sel = results_list.curselection()
        items = [results_list.get(i) for i in sel] if selected_only else list(results_list.get(0, tk.END))
        if not items:
            update_status(status, "No items selected", error=True)
            return
        try:
            created, skipped = apply_understand_goals(storage, sit_var.get(), tgt_var.get(), items)
        except Exception as exc:  # noqa: BLE001
            update_status(status, f"Error: {exc}", error=True)
            return
        update_status(status, f"Created {created}, skipped {skipped}")
        results_list.delete(0, tk.END)
        save_state(STATE_DIR, {
            "situation_ref": sit_var.get(),
            "native_language": nat_var.get(),
            "target_language": tgt_var.get(),
        })

    btn_generate.configure(command=on_generate)
    btn_accept_sel.configure(command=lambda: on_accept(True))
    btn_accept_all.configure(command=lambda: on_accept(False))

    # Enforce API key presence early
    import os

    if not os.getenv("OPENAI_API_KEY"):
        update_status(status, "Set OPENAI_API_KEY before using this tool.", error=True)
        btn_generate.state(["disabled"])
        btn_accept_sel.state(["disabled"])
        btn_accept_all.state(["disabled"])

    on_close(root, lambda: save_state(STATE_DIR, {
        "situation_ref": sit_var.get(),
        "native_language": nat_var.get(),
        "target_language": tgt_var.get(),
    }))

    root.mainloop()


if __name__ == "__main__":
    main()

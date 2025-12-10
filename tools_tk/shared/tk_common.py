from __future__ import annotations

import tkinter as tk
from tkinter import ttk, font
from typing import Callable


def make_root(title: str) -> tk.Tk:
    root = tk.Tk()

    # Fix for HiDPI/4K screens on Linux - scale all default fonts
    # tk scaling often doesn't work on Linux, so we directly modify fonts
    scale_factor = 2.0  # Adjust this value for your 4K screen

    default_font = font.nametofont("TkDefaultFont")
    default_font.configure(size=int(default_font.cget("size") * scale_factor))

    text_font = font.nametofont("TkTextFont")
    text_font.configure(size=int(text_font.cget("size") * scale_factor))

    fixed_font = font.nametofont("TkFixedFont")
    fixed_font.configure(size=int(fixed_font.cget("size") * scale_factor))

    root.title(title)
    root.geometry("900x700")
    return root


def labeled_dropdown(parent, label: str, options: list[tuple[str, str]], default: str | None = None):
    frame = ttk.Frame(parent)
    ttk.Label(frame, text=label).pack(side=tk.LEFT, padx=(0, 8))
    var = tk.StringVar(value=default or (options[0][1] if options else ""))
    menu = ttk.OptionMenu(frame, var, var.get(), *[opt[1] for opt in options], command=lambda _: None)
    # Show nice labels in dropdown text
    if options:
        menu["menu"].delete(0, "end")
        for display, value in options:
            menu["menu"].add_command(label=display, command=lambda v=value: var.set(v))
        var.set(default or options[0][1])
    menu.pack(side=tk.LEFT, fill=tk.X, expand=True)
    return frame, var


def button_row(parent, *buttons: ttk.Button):
    row = ttk.Frame(parent)
    for btn in buttons:
        btn.pack(in_=row, side=tk.LEFT, padx=6)
    return row


def readonly_text(parent) -> tk.Text:
    txt = tk.Text(parent, wrap=tk.NONE)
    txt.configure(state=tk.DISABLED)
    return txt


def set_text(widget: tk.Text, content: str):
    widget.configure(state=tk.NORMAL)
    widget.delete("1.0", tk.END)
    widget.insert(tk.END, content)
    widget.configure(state=tk.DISABLED)


def status_label(parent) -> ttk.Label:
    return ttk.Label(parent, text="", foreground="blue")


def update_status(label: ttk.Label, text: str, *, error: bool = False):
    label.configure(text=text, foreground=("red" if error else "blue"))


def on_close(root: tk.Tk, cleanup: Callable[[], None] | None = None):
    def _handler():
        if cleanup:
            cleanup()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _handler)

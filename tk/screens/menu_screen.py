"""Menu screen for selecting views."""

import tkinter as tk
from tkinter import ttk


class MenuScreen(tk.Frame):
    """Menu screen for selecting which view to open."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.pack(fill="both", expand=True)

        # Title
        title = tk.Label(self, text="Gloss Management", font=("Arial", 24, "bold"))
        title.pack(pady=30)

        # Show active situation
        if self.app.situation_ref:
            info_text = (
                f"Active Situation: {self.app.situation_ref}\n"
                f"Languages: {self.app.native_language} ↔ {self.app.target_language}"
            )
            info = tk.Label(self, text=info_text, font=("Arial", 12), fg="gray")
            info.pack(pady=10)
        else:
            warning = tk.Label(
                self,
                text="⚠ No active situation configured",
                font=("Arial", 12),
                fg="orange",
            )
            warning.pack(pady=10)

        # Menu buttons frame
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=30)

        # Gloss List button
        btn = ttk.Button(
            btn_frame,
            text="Gloss List (Flat)",
            command=self.app.show_gloss_list,
            width=30,
        )
        btn.pack(pady=10)

        # Footer
        footer = tk.Label(
            self, text="Select a view from the menu above", font=("Arial", 10), fg="gray"
        )
        footer.pack(side="bottom", pady=20)

"""Flat gloss list screen with action buttons."""

import tkinter as tk
from tkinter import ttk, messagebox

from src.shared.tree import build_goal_nodes


class GlossListScreen(tk.Frame):
    """Screen showing flat list of all glosses in active situation."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.pack(fill="both", expand=True)

        # Import operations here to avoid circular import
        from tk.operations import BackgroundOperations

        self.ops = BackgroundOperations(app)

        # Header
        self.create_header()

        # Scrollable list
        self.setup_scrollable_list()

        # Load glosses
        self.load_glosses()

    def create_header(self):
        """Create header with title and buttons."""
        header = tk.Frame(self, bg="lightgray")
        header.pack(fill="x", padx=0, pady=0)

        # Title
        tk.Label(
            header,
            text="Glosses in Situation",
            font=("Arial", 18, "bold"),
            bg="lightgray",
        ).pack(side="left", padx=15, pady=10)

        # Buttons
        ttk.Button(header, text="Refresh", command=self.refresh).pack(
            side="right", padx=10, pady=5
        )
        ttk.Button(header, text="← Back to Menu", command=self.app.show_menu).pack(
            side="right", padx=5, pady=5
        )

    def setup_scrollable_list(self):
        """Create scrollable frame for gloss rows."""
        # Create canvas and scrollbar
        canvas = tk.Canvas(self, bg="white")
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg="white")

        self.scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")

        # Bind mousewheel for scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def load_glosses(self):
        """Load and display glosses from situation tree."""
        if not self.app.situation_ref:
            tk.Label(
                self.scrollable_frame,
                text="No active situation configured. Please set a situation first.",
                font=("Arial", 12),
                fg="red",
            ).pack(pady=50)
            return

        try:
            # Load situation
            situation = self.app.storage.resolve_reference(self.app.situation_ref)
            if not situation:
                tk.Label(
                    self.scrollable_frame,
                    text=f"Situation not found: {self.app.situation_ref}",
                    font=("Arial", 12),
                    fg="red",
                ).pack(pady=50)
                return

            # Build tree and collect all glosses
            nodes, stats = build_goal_nodes(
                situation,
                self.app.storage,
                self.app.native_language,
                self.app.target_language,
            )

            # Get all glosses from stats (already deduplicated)
            gloss_refs = sorted(stats.get("situation_glosses", set()))

            if not gloss_refs:
                tk.Label(
                    self.scrollable_frame,
                    text="No glosses found in this situation.",
                    font=("Arial", 12),
                ).pack(pady=50)
                return

            # Load and sort glosses
            glosses = []
            for gloss_ref in gloss_refs:
                gloss = self.app.storage.resolve_reference(gloss_ref)
                if gloss:
                    glosses.append(gloss)

            # Sort by content
            glosses.sort(key=lambda g: g.content.lower())

            # Create header row
            header_row = tk.Frame(self.scrollable_frame, bg="lightgray")
            header_row.pack(fill="x", padx=5, pady=5)

            tk.Label(
                header_row,
                text="Content",
                font=("Arial", 11, "bold"),
                anchor="w",
                width=50,
                bg="lightgray",
            ).pack(side="left", padx=10)

            tk.Label(
                header_row,
                text="Actions",
                font=("Arial", 11, "bold"),
                bg="lightgray",
            ).pack(side="right", padx=10)

            # Create gloss rows
            from tk.widgets.gloss_row import GlossRow

            for gloss in glosses:
                GlossRow(self.scrollable_frame, gloss, self.app, self.ops).pack(
                    fill="x", padx=5, pady=2
                )

            # Summary footer
            summary = tk.Label(
                self.scrollable_frame,
                text=f"Total: {len(glosses)} glosses",
                font=("Arial", 10),
                fg="gray",
            )
            summary.pack(pady=10)

        except Exception as e:
            tk.Label(
                self.scrollable_frame,
                text=f"Error loading glosses: {str(e)}",
                font=("Arial", 12),
                fg="red",
            ).pack(pady=50)

    def refresh(self):
        """Refresh the gloss list."""
        # Clear all children
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Reload glosses
        self.load_glosses()

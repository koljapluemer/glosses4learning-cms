"""Widget for displaying a single gloss with action buttons."""

import tkinter as tk
from tkinter import ttk


class GlossRow(tk.Frame):
    """Row widget displaying a gloss with action buttons."""

    def __init__(self, parent, gloss, app, ops):
        super().__init__(parent, relief="raised", borderwidth=1, bg="white")
        self.gloss = gloss
        self.app = app
        self.ops = ops
        self.ref = f"{gloss.language}:{gloss.slug}"

        # Content label (left side)
        content_text = gloss.content
        # Truncate if too long
        if len(content_text) > 100:
            content_text = content_text[:97] + "..."

        content_label = tk.Label(
            self,
            text=content_text,
            font=("Arial", 11),
            anchor="w",
            width=50,
            bg="white",
        )
        content_label.pack(side="left", padx=10, pady=5)

        # Count relationships
        trans_count = self._count_translations()
        parts_count = len(gloss.parts or [])
        examples_count = len(gloss.usage_examples or [])

        # Action buttons (right side)
        btn_frame = tk.Frame(self, bg="white")
        btn_frame.pack(side="right", padx=5)

        # DEL button
        ttk.Button(
            btn_frame,
            text="DEL",
            width=5,
            command=lambda: self.ops.delete_gloss(self.ref, self),
        ).pack(side="left", padx=2)

        # DIRT button
        ttk.Button(
            btn_frame,
            text="DIRT",
            width=6,
            command=lambda: self.ops.mark_dirty(self.ref),
        ).pack(side="left", padx=2)

        # NOLEARN button
        ttk.Button(
            btn_frame,
            text="NOLEARN",
            width=8,
            command=lambda: self.ops.mark_no_learn(self.ref),
        ).pack(side="left", padx=2)

        # TRANS button
        ttk.Button(
            btn_frame,
            text=f"TRANS ({trans_count})",
            width=12,
            command=lambda: self.ops.generate_translations(self.ref),
        ).pack(side="left", padx=2)

        # EX button
        ttk.Button(
            btn_frame,
            text=f"EX ({examples_count})",
            width=10,
            command=lambda: self.ops.generate_examples(self.ref),
        ).pack(side="left", padx=2)

        # PRT button
        ttk.Button(
            btn_frame,
            text=f"PRT ({parts_count})",
            width=10,
            command=lambda: self.ops.generate_parts(self.ref),
        ).pack(side="left", padx=2)

    def _count_translations(self):
        """Count relevant translations for this gloss."""
        if not self.gloss.translations:
            return 0

        # Determine target language based on gloss language
        if self.gloss.language == self.app.native_language:
            target_lang = self.app.target_language
        elif self.gloss.language == self.app.target_language:
            target_lang = self.app.native_language
        else:
            # Neither native nor target - count all translations
            return len(self.gloss.translations)

        # Count translations in target language
        count = sum(
            1 for ref in self.gloss.translations if ref.startswith(f"{target_lang}:")
        )
        return count

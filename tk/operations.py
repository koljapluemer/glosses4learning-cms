"""Background operation handlers for long-running tasks."""

import threading
import tkinter as tk
from tkinter import messagebox

from src.shared.gloss_actions import (
    delete_gloss_with_cleanup,
    set_needs_human_check,
    set_exclude_from_learning,
    generate_translations_for_gloss,
    generate_parts_for_gloss,
    generate_usage_examples_for_gloss,
)


class BackgroundOperations:
    """Handles async operations with UI feedback."""

    def __init__(self, app):
        self.app = app

    def delete_gloss(self, gloss_ref, row_widget):
        """Delete gloss with confirmation."""
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete {gloss_ref}?\n\n"
            "This will also remove all references to this gloss from other glosses.",
        ):
            return

        try:
            lang, slug = gloss_ref.split(":", 1)
            success, message = delete_gloss_with_cleanup(self.app.storage, lang, slug)

            if success:
                row_widget.destroy()
                messagebox.showinfo("Success", message)
            else:
                messagebox.showerror("Error", message)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete: {str(e)}")

    def mark_dirty(self, gloss_ref):
        """Mark gloss as needing human check."""
        try:
            success, message = set_needs_human_check(
                self.app.storage, gloss_ref, True
            )
            if success:
                messagebox.showinfo("Marked", f"{gloss_ref} marked as DIRT")
            else:
                messagebox.showerror("Error", message)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to mark: {str(e)}")

    def mark_no_learn(self, gloss_ref):
        """Mark gloss to exclude from learning."""
        try:
            success, message = set_exclude_from_learning(
                self.app.storage, gloss_ref, True
            )
            if success:
                messagebox.showinfo("Marked", f"{gloss_ref} marked as NOLEARN")
            else:
                messagebox.showerror("Error", message)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to mark: {str(e)}")

    def generate_translations(self, gloss_ref):
        """Generate translations in background thread."""
        if not self.app.api_key:
            messagebox.showerror(
                "API Key Missing",
                "OpenAI API key not configured. Please set it in the TUI settings.",
            )
            return

        progress = self._show_progress("Generating translations...")

        def task():
            try:
                translations, errors = generate_translations_for_gloss(
                    self.app.storage,
                    gloss_ref,
                    self.app.target_language,
                    self.app.native_language,
                    self.app.api_key,
                )

                # Close progress and show results
                self.app.root.after(0, lambda: progress.destroy())

                if errors:
                    error_msg = "\n".join(errors)
                    self.app.root.after(
                        0, lambda: messagebox.showerror("Errors", error_msg)
                    )
                elif translations:
                    success_msg = f"Generated {len(translations)} translation(s):\n\n" + "\n".join(
                        [f"- {t['text']}" for t in translations[:5]]
                    )
                    if len(translations) > 5:
                        success_msg += f"\n... and {len(translations) - 5} more"
                    self.app.root.after(
                        0, lambda: messagebox.showinfo("Success", success_msg)
                    )
                else:
                    self.app.root.after(
                        0,
                        lambda: messagebox.showwarning(
                            "No Translations", "No translations were generated."
                        ),
                    )

            except Exception as e:
                self.app.root.after(0, lambda: progress.destroy())
                self.app.root.after(
                    0, lambda: messagebox.showerror("Error", f"Failed: {str(e)}")
                )

        threading.Thread(target=task, daemon=True).start()

    def generate_parts(self, gloss_ref):
        """Generate parts in background thread."""
        if not self.app.api_key:
            messagebox.showerror(
                "API Key Missing",
                "OpenAI API key not configured. Please set it in the TUI settings.",
            )
            return

        progress = self._show_progress("Generating parts...")

        def task():
            try:
                parts, errors = generate_parts_for_gloss(
                    self.app.storage, gloss_ref, self.app.api_key
                )

                # Close progress and show results
                self.app.root.after(0, lambda: progress.destroy())

                if errors:
                    error_msg = "\n".join(errors)
                    self.app.root.after(
                        0, lambda: messagebox.showerror("Errors", error_msg)
                    )
                elif parts:
                    success_msg = f"Generated {len(parts)} part(s):\n\n" + "\n".join(
                        [f"- {p}" for p in parts[:10]]
                    )
                    if len(parts) > 10:
                        success_msg += f"\n... and {len(parts) - 10} more"
                    self.app.root.after(
                        0, lambda: messagebox.showinfo("Success", success_msg)
                    )
                else:
                    self.app.root.after(
                        0,
                        lambda: messagebox.showwarning(
                            "No Parts", "No parts were generated."
                        ),
                    )

            except Exception as e:
                self.app.root.after(0, lambda: progress.destroy())
                self.app.root.after(
                    0, lambda: messagebox.showerror("Error", f"Failed: {str(e)}")
                )

        threading.Thread(target=task, daemon=True).start()

    def generate_examples(self, gloss_ref):
        """Generate usage examples in background thread."""
        if not self.app.api_key:
            messagebox.showerror(
                "API Key Missing",
                "OpenAI API key not configured. Please set it in the TUI settings.",
            )
            return

        progress = self._show_progress("Generating usage examples...")

        def task():
            try:
                examples, errors = generate_usage_examples_for_gloss(
                    self.app.storage, gloss_ref, self.app.api_key, num_examples=3
                )

                # Close progress and show results
                self.app.root.after(0, lambda: progress.destroy())

                if errors:
                    error_msg = "\n".join(errors)
                    self.app.root.after(
                        0, lambda: messagebox.showerror("Errors", error_msg)
                    )
                elif examples:
                    success_msg = (
                        f"Generated {len(examples)} example(s):\n\n"
                        + "\n".join([f"- {e}" for e in examples])
                    )
                    self.app.root.after(
                        0, lambda: messagebox.showinfo("Success", success_msg)
                    )
                else:
                    self.app.root.after(
                        0,
                        lambda: messagebox.showwarning(
                            "No Examples", "No examples were generated."
                        ),
                    )

            except Exception as e:
                self.app.root.after(0, lambda: progress.destroy())
                self.app.root.after(
                    0, lambda: messagebox.showerror("Error", f"Failed: {str(e)}")
                )

        threading.Thread(target=task, daemon=True).start()

    def _show_progress(self, message):
        """Show simple progress window."""
        progress = tk.Toplevel(self.app.root)
        progress.title("Working...")
        progress.geometry("400x100")

        tk.Label(progress, text=message, font=("Arial", 12), padx=50, pady=20).pack()

        # Progress bar
        import tkinter.ttk as ttk

        progressbar = ttk.Progressbar(
            progress, mode="indeterminate", length=300, maximum=100
        )
        progressbar.pack(pady=10)
        progressbar.start(10)

        progress.transient(self.app.root)
        progress.grab_set()

        # Center on parent
        progress.update_idletasks()
        x = self.app.root.winfo_x() + (self.app.root.winfo_width() // 2) - (
            progress.winfo_width() // 2
        )
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() // 2) - (
            progress.winfo_height() // 2
        )
        progress.geometry(f"+{x}+{y}")

        return progress

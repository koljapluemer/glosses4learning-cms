"""Main tkinter application."""

import tkinter as tk
from pathlib import Path

from src.shared.state import load_state
from src.shared.storage import GlossStorage


class GlossManagementApp:
    """Main tkinter application for gloss management."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Gloss Management")
        self.root.geometry("1400x800")

        # Load state
        self.state = load_state()
        self.situation_ref = self.state.get("situation_ref")
        self.native_language = self.state.get("native_language")
        self.target_language = self.state.get("target_language")
        self.api_key = self.state.get("settings", {}).get("OPENAI_API_KEY")

        # Initialize storage
        data_root = Path(__file__).resolve().parent.parent / "data"
        self.storage = GlossStorage(data_root)

        # Container for screens
        self.container = tk.Frame(self.root)
        self.container.pack(fill="both", expand=True)

        # Show menu
        self.show_menu()

    def show_menu(self):
        """Show menu screen."""
        self.clear_container()
        from tk.screens.menu_screen import MenuScreen

        MenuScreen(self.container, self)

    def show_gloss_list(self):
        """Show flat gloss list screen."""
        self.clear_container()
        from tk.screens.gloss_list_screen import GlossListScreen

        GlossListScreen(self.container, self)

    def clear_container(self):
        """Clear all widgets in container."""
        for widget in self.container.winfo_children():
            widget.destroy()

    def run(self):
        """Start the application."""
        self.root.mainloop()

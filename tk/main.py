#!/usr/bin/env python3
"""Tkinter UI for gloss management."""

import sys
from pathlib import Path


def main():
    # Add project root to path
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))

    # Import and run app
    from tk.app import GlossManagementApp

    app = GlossManagementApp()
    app.run()


if __name__ == "__main__":
    main()

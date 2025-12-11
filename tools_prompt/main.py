from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools_prompt.menu import main_menu
from tools_tk.shared.gloss_storage import GlossStorage


def main():
    storage = GlossStorage(REPO_ROOT / "data")
    res = main_menu(storage)
    if res == "exit":
        return


if __name__ == "__main__":
    main()

from __future__ import annotations

import sys
from pathlib import Path

from flask import Flask, render_template_string

def find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    return start


HERE = Path(__file__).resolve()
REPO_ROOT = find_repo_root(HERE)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.shared.log import configure_logging
from src.shared.state import load_state
from src.shared.storage import GlossStorage
from src.shared.tree import build_goal_nodes, render_tree_text

app = Flask(__name__)
configure_logging()

HTML_TEMPLATE = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Situation Tree</title>
    <style>
      body { font-family: monospace; white-space: pre; padding: 1rem; }
      .warn { color: #b91c1c; }
    </style>
  </head>
  <body>
    <h3>{{ title }}</h3>
    <div>{{ info }}</div>
    <pre>{{ tree }}</pre>
  </body>
</html>
"""


@app.route("/")
def show_tree():
    state = load_state()
    if not state.get("situation_ref") or not state.get("native_language") or not state.get("target_language"):
        return render_template_string(HTML_TEMPLATE, title="Situation Tree", info="Set situation/native/target in state.json", tree="(no data)")

    storage = GlossStorage(REPO_ROOT / "data")
    situation = storage.resolve_reference(state["situation_ref"])
    if not situation:
        return render_template_string(HTML_TEMPLATE, title="Situation Tree", info=f"Missing situation {state['situation_ref']}", tree="(no data)")

    nodes, stats = build_goal_nodes(
        situation,
        storage=storage,
        native_language=state["native_language"],
        target_language=state["target_language"],
    )
    tree_text = render_tree_text(nodes) or "(no tree)"
    info = f"Native: {state['native_language']} | Target: {state['target_language']}"
    return render_template_string(HTML_TEMPLATE, title=situation.content, info=info, tree=tree_text)


if __name__ == "__main__":
    app.run(debug=True)

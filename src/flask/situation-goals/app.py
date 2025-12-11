from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

from flask import Flask, redirect, render_template, request, url_for

HERE = Path(__file__).resolve()
APP_DIR = HERE.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

REPO_ROOT = next((p for p in HERE.parents if (p / "pyproject.toml").exists()), APP_DIR)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.shared.languages import load_language  # noqa: E402
from src.shared.log import configure_logging  # noqa: E402
from src.shared.storage import Gloss, GlossStorage, normalize_language_code  # noqa: E402
from src.shared.tree import detect_goal_type, determine_goal_state  # noqa: E402

configure_logging()
storage = GlossStorage(REPO_ROOT / "data")

app = Flask(__name__, template_folder="templates")
app.config["TEMPLATES_AUTO_RELOAD"] = True


def _language_options(glosses: Iterable[Gloss]) -> list[dict[str, str]]:
    codes = sorted({normalize_language_code(g.language) for g in glosses if g.language})
    items: list[dict[str, str]] = []
    for code in codes:
        meta = load_language(code) or {}
        label = meta.get("displayName") or meta.get("name") or code
        items.append({"code": code, "label": label})
    return items


def _situations(glosses: Iterable[Gloss]) -> list[Gloss]:
    return sorted(
        (g for g in glosses if "eng:situation" in (g.tags or [])),
        key=lambda g: g.content.lower(),
    )


@app.route("/", methods=["GET", "POST"])
def choose_languages():
    glosses = storage.list_glosses()
    languages = _language_options(glosses)
    default_native = normalize_language_code(request.values.get("native")) or (languages[0]["code"] if languages else "")
    default_target = normalize_language_code(request.values.get("target")) or (
        languages[1]["code"] if len(languages) > 1 else default_native
    )

    if request.method == "POST":
        native = normalize_language_code(request.form.get("native"))
        target = normalize_language_code(request.form.get("target"))
        if native and target:
            return redirect(url_for("list_situations", native=native, target=target))

    return render_template(
        "select_languages.html",
        languages=languages,
        native_language=default_native,
        target_language=default_target,
    )


@app.route("/situations")
def list_situations():
    native_language = normalize_language_code(request.args.get("native"))
    target_language = normalize_language_code(request.args.get("target"))
    if not (native_language and target_language):
        return redirect(url_for("choose_languages"))

    glosses = storage.list_glosses()

    situations = _situations(glosses)
    situation_rows: list[dict[str, object]] = []
    for situation in situations:
        goals: list[dict[str, object]] = []
        for child_ref in situation.children or []:
            goal = storage.resolve_reference(child_ref)
            if not goal:
                continue
            kind = detect_goal_type(goal, native_language, target_language)
            if not kind:
                continue
            display_kind = "paraphrased-expression" if kind == "procedural" else "understanding"
            state = determine_goal_state(goal, storage, native_language, target_language)
            goals.append({"goal": goal, "kind": display_kind, "state": state})
        goals.sort(key=lambda g: (g["kind"], g["goal"].content.lower()))
        situation_rows.append({"situation": situation, "goals": goals})

    return render_template(
        "situation_goals.html",
        native_language=native_language,
        target_language=target_language,
        situations=situation_rows,
    )


if __name__ == "__main__":
    app.run(debug=True)

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from prompt_toolkit.shortcuts import ProgressBar, message_dialog

from src.shared.storage import GlossStorage
from src.shared.tree import build_goal_nodes

logger = logging.getLogger(__name__)


def _load_language_codes(data_root: Path) -> list[str]:
    lang_dir = data_root / "language"
    codes: list[str] = []
    if not lang_dir.exists():
        logger.error("Language directory not found: %s", lang_dir)
        return codes
    for path in sorted(lang_dir.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            code = str(data.get("isoCode") or data.get("iso_code") or path.stem).strip().lower()
            if code and code not in codes:
                codes.append(code)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to read language file %s: %s", path, exc)
    return codes


def _node_ref(node: dict[str, Any]) -> str:
    gl = node["gloss"]
    return f"{gl.language}:{gl.slug or gl.content}"


def _gather_refs(root_node: dict[str, Any]) -> tuple[list[str], list[str]]:
    refs: list[str] = []
    learn_refs: list[str] = []
    seen: set[str] = set()
    skip_parts = root_node.get("goal_type") == "procedural"

    def walk(node: dict[str, Any]):
        if skip_parts and node.get("role") in ("part", "usage_part"):
            return
        ref = _node_ref(node)
        if ref not in seen:
            seen.add(ref)
            refs.append(ref)
        if node.get("bold") and ref != _node_ref(root_node) and ref not in learn_refs:
            learn_refs.append(ref)
        for child in node.get("children", []):
            walk(child)

    walk(root_node)
    return refs, learn_refs


def _build_export_payload(
    storage: GlossStorage, situation, native_language: str, target_language: str
) -> tuple[dict[str, Any] | None, str | None]:
    goal_nodes, _stats = build_goal_nodes(
        situation,
        storage=storage,
        native_language=native_language,
        target_language=target_language,
    )
    if not goal_nodes:
        return None, "No learnable content"

    export_obj: dict[str, list[dict[str, Any]]] = {
        "procedural-paraphrase-expression-goals": [],
        "understand-expression-goals": [],
    }
    all_refs: set[str] = set()

    situation_ref = f"{situation.language}:{situation.slug or situation.content}"
    all_refs.add(situation_ref)
    for ref in situation.translations or []:
        if ref.startswith(f"{native_language}:") or ref.startswith(f"{target_language}:"):
            all_refs.add(ref)

    for root in goal_nodes:
        # Skip goals that are not at least yellow (only export yellow/green)
        state = (root.get("state") or "").lower()
        if state not in ("yellow", "green"):
            continue
        goal_type = root.get("goal_type")
        if goal_type not in ("procedural", "understand"):
            continue
        refs, learn_refs = _gather_refs(root)
        all_refs.update(refs)
        payload = {
            "finalChallenge": _node_ref(root),
            "needToBeLearned": learn_refs,
            "references": refs,
        }
        if goal_type == "procedural":
            export_obj["procedural-paraphrase-expression-goals"].append(payload)
        else:
            export_obj["understand-expression-goals"].append(payload)

    if not export_obj["procedural-paraphrase-expression-goals"] and not export_obj["understand-expression-goals"]:
        return None, "No learnable content"

    jsonl_lines = []
    excluded_count = 0
    for ref in sorted(all_refs):
        gloss = storage.resolve_reference(ref)
        if not gloss:
            continue
        # Skip glosses flagged for exclusion
        if getattr(gloss, "needsHumanCheck", False) or getattr(gloss, "excludeFromLearning", False):
            excluded_count += 1
            continue
        item = gloss.to_dict()
        item["ref"] = ref
        jsonl_lines.append(json.dumps(item, ensure_ascii=False))

    stats = {
        "goal_count": len(goal_nodes),
        "gloss_count": len(all_refs),
        "excluded_count": excluded_count,
    }
    return (
        {
            "export_obj": export_obj,
            "jsonl": "\n".join(jsonl_lines),
            "stats": stats,
            "situation_ref": situation_ref,
        },
        None,
    )


def perform_batch_export(storage: GlossStorage) -> dict[str, Any]:
    output_root = Path(getattr(storage, "data_root", Path("."))).resolve().parent / "situations"
    result: dict[str, Any] = {
        "success": False,
        "error": None,
        "total_situations": 0,
        "total_exports": 0,
        "exports": [],
        "skipped": [],
        "output_root": str(output_root),
    }
    try:
        situations = [g for g in storage.list_glosses() if "eng:situation" in (g.tags or [])]
        result["total_situations"] = len(situations)
        if not situations:
            result["success"] = True
            return result

        languages = _load_language_codes(Path(getattr(storage, "data_root", Path("."))))
        if len(languages) < 2:
            result["error"] = "Need at least 2 configured languages"
            return result

        combos = [
            (situation, native_lang, target_lang)
            for situation in situations
            for native_lang in languages
            for target_lang in languages
            if native_lang != target_lang
        ]
        if not combos:
            result["error"] = "No language combinations to export"
            return result

        with ProgressBar(title="Exporting situations") as pb:
            for situation, native_lang, target_lang in pb(combos):
                payload, skip_reason = _build_export_payload(storage, situation, native_lang, target_lang)
                if not payload:
                    result["skipped"].append(
                        {
                            "situation": f"{situation.language}:{situation.slug}",
                            "native": native_lang,
                            "target": target_lang,
                            "reason": skip_reason or "Unknown reason",
                        }
                    )
                    continue

                output_dir = output_root / native_lang / target_lang
                output_dir.mkdir(parents=True, exist_ok=True)

                base_filename = situation.content
                situation_json_path = output_dir / f"{base_filename}.json"
                glosses_jsonl_path = output_dir / f"{base_filename}.jsonl"

                situation_json_path.write_text(json.dumps(payload["export_obj"], ensure_ascii=False, indent=2), encoding="utf-8")
                glosses_jsonl_path.write_text(payload["jsonl"], encoding="utf-8")

                result["exports"].append(
                    {
                        "situation": f"{situation.language}:{situation.slug}",
                        "native": native_lang,
                        "target": target_lang,
                        "situation_json": str(situation_json_path),
                        "glosses_jsonl": str(glosses_jsonl_path),
                        "stats": payload["stats"],
                    }
                )
                result["total_exports"] += 1

        result["success"] = True
        return result
    except Exception as exc:  # noqa: BLE001
        logger.exception("Batch export failed")
        result["error"] = str(exc)
        result["success"] = False
        return result


def flow_export_situations_batch(storage: GlossStorage, state: dict) -> None:  # noqa: ARG001
    """
    Export all situations for every native/target language pair to the situations/ directory.
    """
    result = perform_batch_export(storage)
    if not result.get("success"):
        message_dialog(
            title="Batch export failed",
            text=f"Error: {result.get('error') or 'Unknown error'}\nSee log for details.",
        ).run()
        return

    summary_lines = [
        f"Output directory: {result.get('output_root')}",
        f"Situations scanned: {result.get('total_situations')}",
        f"Exports written: {result.get('total_exports')}",
    ]
    skipped = result.get("skipped") or []
    if skipped:
        summary_lines.append(f"Skipped combinations: {len(skipped)}")
    message_dialog(title="Batch export complete", text="\n".join(summary_lines)).run()

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Any

from markupsafe import Markup

from sbll_cms.entities.gloss import Gloss
from sbll_cms.utils import paraphrase_display

SPLIT_LOG_MARKER = "SPLIT_CONSIDERED_UNNECESSARY"
TRANSLATION_IMPOSSIBLE_MARKER = "TRANSLATION_CONSIDERED_IMPOSSIBLE"
USAGE_IMPOSSIBLE_MARKER = "USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE"


def build_goal_nodes(situation: Gloss, storage, native_language: str, target_language: str):
    stats = {
        "situation_glosses": set(),
        "glosses_to_learn": set(),
        "native_missing": set(),
        "target_missing": set(),
        "parts_missing": set(),
        "usage_missing": set(),
        "gloss_map": {},
    }
    seen_keys: set[str] = set()
    nodes = []

    def gloss_key(gl):
        return f"{gl.language}:{gl.slug or gl.content}"

    def has_log(gl, marker: str) -> bool:
        logs = getattr(gl, "logs", {}) or {}
        if not isinstance(logs, dict):
            return False
        return any(marker in str(val) for val in logs.values())

    def has_translation(gl, lang: str) -> bool:
        return any(ref.startswith(f"{lang}:") for ref in (gl.translations or []))

    def mark_stats(gl, usage_lineage: bool, parts_line: bool, learn_lang: str):
        key = gloss_key(gl)
        stats["gloss_map"][key] = gl
        stats["situation_glosses"].add(key)

        if not (getattr(gl, "parts", None) or []) and not has_log(gl, SPLIT_LOG_MARKER):
            stats["parts_missing"].add(key)

        if gl.language == target_language:
            if not has_translation(gl, native_language) and not has_log(gl, f"{TRANSLATION_IMPOSSIBLE_MARKER}:{native_language}"):
                stats["native_missing"].add(key)
            if not usage_lineage and not has_log(gl, f"{USAGE_IMPOSSIBLE_MARKER}:{target_language}") and not (gl.usage_examples or []):
                stats["usage_missing"].add(key)
        elif gl.language == native_language:
            if not has_translation(gl, target_language) and not has_log(gl, f"{TRANSLATION_IMPOSSIBLE_MARKER}:{target_language}"):
                stats["target_missing"].add(key)

        if parts_line and gl.language == learn_lang:
            stats["glosses_to_learn"].add(key)

        return {
            "warn_native_missing": key in stats["native_missing"],
            "warn_target_missing": key in stats["target_missing"],
            "warn_usage_missing": key in stats["usage_missing"],
        }

    def build_node(gloss, role="root", marker="", usage_lineage=False, allow_translations=True, path=None, parts_line=False, learn_lang=""):
        tags = gloss.tags or []
        if gloss.language == target_language and "eng:paraphrase" in tags:
            return None

        path = set(path or [])
        key = gloss_key(gloss)
        seen_keys.add(key)

        flags = mark_stats(gloss, usage_lineage, parts_line, learn_lang)

        node = {
            "gloss": gloss,
            "children": [],
            "marker": marker,
            "bold": parts_line and gloss.language == learn_lang,
            "role": role,
            "warn_native_missing": flags["warn_native_missing"],
            "warn_target_missing": flags["warn_target_missing"],
            "warn_usage_missing": flags["warn_usage_missing"],
            "warn_parts_missing": key in stats["parts_missing"],
        }

        if key in path:
            return node
        next_path = set(path or [])
        next_path.add(key)

        if role in ("root", "part", "usage_part"):
            stats["glosses_to_learn"].add(key)

        for part_ref in getattr(gloss, "parts", []):
            part_gloss = storage.resolve_reference(part_ref)
            if not part_gloss:
                continue
            child_parts_line = parts_line if role == "root" else False
            part_node = build_node(
                part_gloss,
                role="usage_part" if role in ("usage", "usage_part") else "part",
                usage_lineage=usage_lineage,
                allow_translations=True,
                path=next_path,
                parts_line=child_parts_line,
                learn_lang=learn_lang,
            )
            if part_node:
                node["children"].append(part_node)

        if allow_translations:
            other_lang = None
            if gloss.language == native_language and target_language:
                other_lang = target_language
            elif gloss.language == target_language and native_language:
                other_lang = native_language
            if other_lang:
                for ref in gloss.translations or []:
                    ref_lang = ref.split(":", 1)[0].strip().lower()
                    if ref_lang != other_lang.lower():
                        continue
                    t_gloss = storage.resolve_reference(ref)
                    if not t_gloss:
                        continue
                    child_key = gloss_key(t_gloss)
                    t_node = build_node(
                        t_gloss,
                        role="translation",
                        marker="",
                        usage_lineage=usage_lineage,
                        allow_translations=child_key not in next_path,
                        path=next_path,
                        parts_line=False,
                        learn_lang=learn_lang,
                    )
                    if t_node:
                        node["children"].append(t_node)

        if gloss.language == target_language and not usage_lineage:
            if gloss.usage_examples:
                for u_ref in getattr(gloss, "usage_examples", []):
                    u_gloss = storage.resolve_reference(u_ref)
                    if not u_gloss:
                        continue
                    usage_node = build_node(
                        u_gloss,
                        role="usage",
                        marker="🛠 ",
                        usage_lineage=True,
                        allow_translations=True,
                        path=next_path,
                        parts_line=False,
                        learn_lang=learn_lang,
                    )
                    if usage_node:
                        node["children"].append(usage_node)

        return node

    for ref in situation.children:
        gloss = storage.resolve_reference(ref)
        if not gloss:
            continue
        tags = gloss.tags or []
        marker = ""
        if gloss.language == native_language and "eng:procedural-paraphrase-expression-goal" in tags:
            marker = "⚙︎ "
            learn_lang = native_language
            goal_type = "procedural"
        elif gloss.language == target_language and "eng:understand-expression-goal" in tags:
            marker = "🗣 "
            learn_lang = target_language
            goal_type = "understand"
        else:
            continue
        node = build_node(
            gloss,
            role="root",
            marker=marker,
            usage_lineage=False,
            allow_translations=True,
            parts_line=True,
            learn_lang=learn_lang,
        )
        if node:
            node["goal_type"] = goal_type
            nodes.append(node)
    return nodes, stats


def render_tree(nodes: list[dict[str, Any]]):
    lines: list[str] = []

    def label_for(node):
        gloss = node["gloss"]
        text = paraphrase_display(gloss)
        slug = gloss.slug or ""
        url = f"/glosses/{gloss.language}/{slug}/edit"
        markers_after = ""
        if node.get("warn_native_missing") or node.get("warn_target_missing"):
            markers_after += " ⚠"
        if node.get("warn_usage_missing"):
            markers_after += " 🛠?"
        if node.get("warn_parts_missing"):
            markers_after += " ⫼?"
        content = f'<a class="link link-primary" target="_blank" href="{url}">{text}</a>{markers_after}'
        if node.get("bold"):
            content = f"<strong>{content}</strong>"
        return Markup(content)

    def walk(node_list, prefix=""):
        total = len(node_list)
        for idx, node in enumerate(node_list):
            is_last = idx == total - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{node.get('marker', '')}{label_for(node)}")
            if node.get("children"):
                walk(node["children"], f"{prefix}{'    ' if is_last else '│   '}")

    walk(nodes)
    return lines


def collect_situation_stats(storage, situation: Gloss, native_language: str, target_language: str):
    """
    Return only the aggregated stats for a situation; used by tool routes that
    need the missing refs without rendering the tree.
    """
    _nodes, stats = build_goal_nodes(
        situation,
        storage=storage,
        native_language=native_language,
        target_language=target_language,
    )
    return stats


def create_situation_export_zip(situation, storage, native_language: str, target_language: str):
    goal_nodes, stats = build_goal_nodes(
        situation,
        storage=storage,
        native_language=native_language,
        target_language=target_language,
    )
    if not goal_nodes:
        return None, stats

    def node_ref(node):
        gl = node["gloss"]
        return f"{gl.language}:{gl.slug or gl.content}"

    def gather_refs(root_node):
        refs = []
        learn_refs = []
        seen = set()

        def walk(n):
            ref = node_ref(n)
            if ref not in seen:
                seen.add(ref)
                refs.append(ref)
            if n.get("bold") and ref != node_ref(root_node):
                if ref not in learn_refs:
                    learn_refs.append(ref)
            for child in n.get("children", []):
                walk(child)

        walk(root_node)
        return refs, learn_refs

    export_obj = {
        "procedural-paraphrase-expression-goals": [],
        "understand-expression-goals": [],
    }
    all_refs: set[str] = set()

    all_refs.add(f"{situation.language}:{situation.slug}")
    for ref in situation.translations or []:
        if ref.startswith(f"{native_language}:") or ref.startswith(f"{target_language}:"):
            all_refs.add(ref)

    for root in goal_nodes:
        goal_type = root.get("goal_type")
        if goal_type not in ("procedural", "understand"):
            continue
        refs, learn_refs = gather_refs(root)
        all_refs.update(refs)
        payload = {
            "finalChallenge": node_ref(root),
            "needToBeLearned": learn_refs,
            "references": refs,
        }
        if goal_type == "procedural":
            export_obj["procedural-paraphrase-expression-goals"].append(payload)
        else:
            export_obj["understand-expression-goals"].append(payload)

    jsonl_lines = []
    for ref in all_refs:
        gloss = storage.resolve_reference(ref)
        if not gloss:
            continue
        item = gloss.to_dict()
        item["ref"] = ref
        jsonl_lines.append(json.dumps(item, ensure_ascii=False))

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("situation.json", json.dumps(export_obj, ensure_ascii=False, indent=2))
        zf.writestr("glosses.jsonl", "\n".join(jsonl_lines))
    buf.seek(0)

    stats["goal_count"] = len(goal_nodes)
    stats["gloss_count"] = len(all_refs)

    return buf, stats


def perform_batch_export(storage, language_store, output_root):
    result = {
        "success": False,
        "total_situations": 0,
        "total_exports": 0,
        "exports": [],
        "skipped": [],
        "error": None,
    }
    try:
        situations = []
        for g in storage.list_glosses():
            tags = g.tags or []
            if any(t == "eng:situation" for t in tags):
                situations.append(g)
        result["total_situations"] = len(situations)
        if not situations:
            result["success"] = True
            return result

        languages = language_store.list_languages()
        if len(languages) < 2:
            result["error"] = "Need at least 2 configured languages"
            return result

        for situation in situations:
            for native_lang in languages:
                for target_lang in languages:
                    if native_lang.iso_code == target_lang.iso_code:
                        continue
                    goal_nodes, stats = build_goal_nodes(
                        situation, storage=storage,
                        native_language=native_lang.iso_code,
                        target_language=target_lang.iso_code
                    )
                    if not goal_nodes:
                        result["skipped"].append({
                            "situation": f"{situation.language}:{situation.slug}",
                            "native": native_lang.iso_code,
                            "target": target_lang.iso_code,
                            "reason": "No learnable content",
                        })
                        continue

                    def node_ref(node):
                        gl = node["gloss"]
                        return f"{gl.language}:{gl.slug or gl.content}"

                    def gather_refs(root_node):
                        refs = []
                        learn_refs = []
                        seen = set()

                        def walk(n):
                            ref = node_ref(n)
                            if ref not in seen:
                                seen.add(ref)
                                refs.append(ref)
                            if n.get("bold") and ref != node_ref(root_node):
                                if ref not in learn_refs:
                                    learn_refs.append(ref)
                            for child in n.get("children", []):
                                walk(child)

                        walk(root_node)
                        return refs, learn_refs

                    export_obj = {
                        "procedural-paraphrase-expression-goals": [],
                        "understand-expression-goals": [],
                    }
                    all_refs: set[str] = set()

                    all_refs.add(f"{situation.language}:{situation.slug}")
                    for ref in situation.translations or []:
                        if ref.startswith(f"{native_lang.iso_code}:") or ref.startswith(f"{target_lang.iso_code}:"):
                            all_refs.add(ref)

                    for root in goal_nodes:
                        goal_type = root.get("goal_type")
                        if goal_type not in ("procedural", "understand"):
                            continue
                        refs, learn_refs = gather_refs(root)
                        all_refs.update(refs)
                        payload = {
                            "finalChallenge": node_ref(root),
                            "needToBeLearned": learn_refs,
                            "references": refs,
                        }
                        if goal_type == "procedural":
                            export_obj["procedural-paraphrase-expression-goals"].append(payload)
                        else:
                            export_obj["understand-expression-goals"].append(payload)

                    jsonl_lines = []
                    for ref in all_refs:
                        gloss = storage.resolve_reference(ref)
                        if not gloss:
                            continue
                        item = gloss.to_dict()
                        item["ref"] = ref
                        jsonl_lines.append(json.dumps(item, ensure_ascii=False))

                    output_dir = Path(output_root) / native_lang.iso_code / target_lang.iso_code
                    output_dir.mkdir(parents=True, exist_ok=True)

                    base_filename = situation.content
                    situation_json_path = output_dir / f"{base_filename}.json"
                    with situation_json_path.open("w", encoding="utf-8") as f:
                        json.dump(export_obj, f, ensure_ascii=False, indent=2)
                    glosses_jsonl_path = output_dir / f"{base_filename}.jsonl"
                    with glosses_jsonl_path.open("w", encoding="utf-8") as f:
                        f.write("\n".join(jsonl_lines))

                    result["exports"].append({
                        "situation": f"{situation.language}:{situation.slug}",
                        "native": native_lang.iso_code,
                        "target": target_lang.iso_code,
                        "situation_json": str(situation_json_path),
                        "glosses_jsonl": str(glosses_jsonl_path),
                        "stats": {
                            "goal_count": len(goal_nodes),
                            "gloss_count": len(all_refs),
                        },
                    })
                    result["total_exports"] += 1

        result["success"] = True
        return result

    except Exception as e:  # noqa: BLE001
        result["error"] = str(e)
        result["success"] = False
        raise

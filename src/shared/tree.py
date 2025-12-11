from __future__ import annotations

from typing import Any

from src.shared.storage import Gloss, GlossStorage

SPLIT_LOG_MARKER = "SPLIT_CONSIDERED_UNNECESSARY"
TRANSLATION_IMPOSSIBLE_MARKER = "TRANSLATION_CONSIDERED_IMPOSSIBLE"
USAGE_IMPOSSIBLE_MARKER = "USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE"


def paraphrase_display(gloss: Gloss) -> str:
    text = gloss.content or gloss.slug or ""
    if gloss.slug and gloss.slug not in text:
        text = f"{text} ({gloss.slug})"
    return text


def build_goal_nodes(situation: Gloss, storage: GlossStorage, native_language: str, target_language: str):
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
                        marker="USG ",
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
            marker = "PROC "
            learn_lang = native_language
            goal_type = "procedural"
        elif gloss.language == target_language and "eng:understand-expression-goal" in tags:
            marker = "UNDR "
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


def render_tree_text(nodes: list[dict[str, Any]]) -> str:
    lines: list[str] = []

    def label_for(node):
        gloss = node["gloss"]
        text = paraphrase_display(gloss)
        markers_after = ""
        if node.get("warn_native_missing") or node.get("warn_target_missing"):
            markers_after += " [WARN-TRANSLATION]"
        if node.get("warn_usage_missing"):
            markers_after += " [WARN-USAGE]"
        if node.get("warn_parts_missing"):
            markers_after += " [WARN-PARTS]"
        content = f"{text}{markers_after}"
        if node.get("bold"):
            content = f"*{content}*"
        return content

    def walk(node_list, prefix=""):
        total = len(node_list)
        for idx, node in enumerate(node_list):
            is_last = idx == total - 1
            connector = "`-- " if is_last else "|-- "
            lines.append(f"{prefix}{connector}{node.get('marker', '')}{label_for(node)}")
            if node.get("children"):
                walk(node["children"], f"{prefix}{'    ' if is_last else '|   '}")

    walk(nodes)
    return "\n".join(lines)


def collect_situation_stats(storage: GlossStorage, situation: Gloss, native_language: str, target_language: str):
    _nodes, stats = build_goal_nodes(
        situation,
        storage=storage,
        native_language=native_language,
        target_language=target_language,
    )
    return stats

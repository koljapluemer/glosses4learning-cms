from __future__ import annotations

from typing import Any

from src.shared.storage import Gloss, GlossStorage, normalize_language_code

SPLIT_LOG_MARKER = "SPLIT_CONSIDERED_UNNECESSARY"
TRANSLATION_IMPOSSIBLE_MARKER = "TRANSLATION_CONSIDERED_IMPOSSIBLE"
USAGE_IMPOSSIBLE_MARKER = "USAGE_EXAMPLE_CONSIDERED_IMPOSSIBLE"


def detect_goal_type(gloss: Gloss, native_language: str, target_language: str) -> str | None:
    """Return normalized goal type for situation children or None if not a goal."""
    lang = normalize_language_code(gloss.language)
    native = normalize_language_code(native_language)
    target = normalize_language_code(target_language)
    tags = gloss.tags or []
    if lang == native and "eng:procedural-paraphrase-expression-goal" in tags:
        return "procedural"
    if lang == target and "eng:understand-expression-goal" in tags:
        return "understanding"
    return None


def evaluate_goal_state(gloss: Gloss, storage: GlossStorage, native_language: str, target_language: str) -> dict[str, str | list[str]]:
    """
    Compute RED/YELLOW/GREEN for a goal in the context of native/target languages and
    return a detailed log of checks.
    Rules in doc/reference_what_is_a_valid_goal.md.
    """
    native = normalize_language_code(native_language)
    target = normalize_language_code(target_language)
    goal_lang = normalize_language_code(gloss.language)
    tags = gloss.tags or []

    def _translation_refs(g: Gloss, lang: str, *, require_non_paraphrase: bool = False) -> list[str]:
        matches: list[str] = []
        for ref in getattr(g, "translations", []) or []:
            ref_lang = ref.split(":", 1)[0].strip().lower()
            if ref_lang != lang:
                continue
            t_gloss = storage.resolve_reference(ref)
            if not t_gloss:
                continue
            if require_non_paraphrase and "eng:paraphrase" in (t_gloss.tags or []):
                continue
            matches.append(f"{t_gloss.language}:{t_gloss.slug or t_gloss.content}")
        return matches

    def _parts() -> list[Gloss]:
        items: list[Gloss] = []
        for ref in getattr(gloss, "parts", []) or []:
            p = storage.resolve_reference(ref)
            if p:
                items.append(p)
        return items

    def _translations_to(gl: Gloss, lang: str, *, require_non_paraphrase: bool = False) -> list[Gloss]:
        matches: list[Gloss] = []
        for ref in getattr(gl, "translations", []) or []:
            ref_lang = ref.split(":", 1)[0].strip().lower()
            if ref_lang != lang:
                continue
            t_gloss = storage.resolve_reference(ref)
            if not t_gloss:
                continue
            if require_non_paraphrase and "eng:paraphrase" in (t_gloss.tags or []):
                continue
            matches.append(t_gloss)
        return matches

    def _translations_to(gl: Gloss, lang: str, *, require_non_paraphrase: bool = False) -> list[Gloss]:
        matches: list[Gloss] = []
        for ref in getattr(gl, "translations", []) or []:
            ref_lang = ref.split(":", 1)[0].strip().lower()
            if ref_lang != lang:
                continue
            t_gloss = storage.resolve_reference(ref)
            if not t_gloss:
                continue
            if require_non_paraphrase and "eng:paraphrase" in (t_gloss.tags or []):
                continue
            matches.append(t_gloss)
        return matches

    goal_kind = detect_goal_type(gloss, native, target)
    goal_ref = f"{gloss.language}:{gloss.slug or gloss.content}"
    lines: list[str] = [
        f"goal={goal_ref}",
        f"kind={goal_kind or 'unknown'}",
        f"native={native}",
        f"target={target}",
    ]

    def _section(title: str):
        lines.append(f"{title}:")

    def _check(desc: str, passed: bool, missing: list[str] | None = None):
        lines.append(f"- [{'x' if passed else ' '}] {desc}")
        if not passed and missing:
            for item in missing:
                lines.append(f"  missing: {item}")
        return passed

    yellow_ok = False
    green_ok = False

    if goal_kind == "understanding":
        _section("yellow_requirements")
        c_lang = _check("goal expression is in target language", goal_lang == target, missing=[goal_ref])
        goal_native_trans = _translation_refs(gloss, native)
        c_t1 = _check(
            "goal has >=1 translation into native",
            len(goal_native_trans) >= 1,
            missing=[goal_ref] if len(goal_native_trans) < 1 else None,
        )
        parts = _parts()
        c_parts = _check("goal has parts", bool(parts), missing=[goal_ref])
        missing_parts_trans: list[str] = []
        for part in parts:
            part_trans = _translation_refs(part, native)
            if len(part_trans) < 1:
                missing_parts_trans.append(f"{part.language}:{part.slug or part.content}")
        c_parts_trans = _check(
            "each part has >=1 translation to native",
            not missing_parts_trans,
            missing=missing_parts_trans,
        )
        yellow_ok = all([c_lang, c_t1, c_parts, c_parts_trans])

        _section("green_requirements")
        if yellow_ok:
            c_t2 = _check(
                "goal has >=2 translations into native",
                len(goal_native_trans) >= 2,
                missing=[goal_ref],
            )
            missing_parts_usage: list[str] = []
            for part in parts:
                usable_examples = []
                lacking_examples = []
                for u_ref in getattr(part, "usage_examples", []) or []:
                    usage_gloss = storage.resolve_reference(u_ref)
                    if not usage_gloss:
                        lacking_examples.append(f"{u_ref} (missing gloss)")
                        continue
                    if _translation_refs(usage_gloss, native):
                        usable_examples.append(f"{usage_gloss.language}:{usage_gloss.slug or usage_gloss.content}")
                    else:
                        lacking_examples.append(f"{usage_gloss.language}:{usage_gloss.slug or usage_gloss.content}")
                if len(usable_examples) < 2:
                    detail = f"{part.language}:{part.slug or part.content} (usable: {', '.join(usable_examples) or 'none'}; lacking native translation on: {', '.join(lacking_examples) or 'none'})"
                    missing_parts_usage.append(detail)
            c_parts_usage = _check(
                "each part has >=2 usage examples translated once to native",
                not missing_parts_usage,
                missing=missing_parts_usage,
            )
            green_ok = c_t2 and c_parts_usage
        else:
            _check("reach yellow first", False, missing=[goal_ref])

    elif goal_kind == "procedural":
        _section("yellow_requirements")
        c_lang = _check("goal expression is in native language", goal_lang == native, missing=[goal_ref])
        c_tag = _check("goal tagged eng:paraphrase", "eng:paraphrase" in tags, missing=[goal_ref])
        goal_target_trans_glosses = _translations_to(gloss, target)
        c_t1 = _check(
            "goal has >=1 translation into target",
            len(goal_target_trans_glosses) >= 1,
            missing=[goal_ref],
        )
        # For procedural paraphrases: do not require parts on the goal itself.
        # Require each translated target expression to have parts, and those parts to translate back to native.
        missing_parts = []
        missing_parts_trans: list[str] = []
        for t_gloss in goal_target_trans_glosses:
            t_parts = getattr(t_gloss, "parts", []) or []
            if not t_parts:
                missing_parts.append(f"{t_gloss.language}:{t_gloss.slug or t_gloss.content}")
                continue
            for part_ref in t_parts:
                part = storage.resolve_reference(part_ref)
                if not part:
                    missing_parts_trans.append(f"{part_ref} (missing gloss)")
                    continue
                back_trans = _translation_refs(part, native)
                if len(back_trans) < 1:
                    missing_parts_trans.append(f"{part.language}:{part.slug or part.content}")
        c_parts = _check("each target translation has parts", not missing_parts, missing=missing_parts)
        c_parts_trans = _check(
            "each part of each target translation has >=1 translation to native",
            not missing_parts_trans,
            missing=missing_parts_trans,
        )
        yellow_ok = all([c_lang, c_tag, c_t1, c_parts, c_parts_trans])

        _section("green_requirements")
        if yellow_ok:
            c_t2 = _check(
                "goal has >=2 translations into target",
                len(goal_target_trans_glosses) >= 2,
                missing=[goal_ref],
            )
            green_ok = c_t2
        else:
            _check("reach yellow first", False, missing=[goal_ref])

    else:
        _section("yellow_requirements")
        _check("goal matches expected kind for native/target languages", False, missing=[goal_ref])
        _section("green_requirements")
        _check("reach yellow first", False, missing=[goal_ref])

    state = "green" if green_ok else "yellow" if yellow_ok else "red"
    lines.append(f"state={state}")
    return {"state": state, "log": "\n".join(lines)}


def determine_goal_state(gloss: Gloss, storage: GlossStorage, native_language: str, target_language: str) -> str:
    """Backward-compatible helper returning only the state."""
    return evaluate_goal_state(gloss, storage, native_language, target_language)["state"]


def paraphrase_display(gloss: Gloss) -> str:
    text = gloss.content or gloss.slug or ""
    if gloss.slug and gloss.slug not in text:
        text = f"{text} ({gloss.slug})"
    if "eng:paraphrase" in (gloss.tags or []):
        return f"[{text}]"
    return text


def build_goal_nodes(situation: Gloss, storage: GlossStorage, native_language: str, target_language: str):
    native_language = normalize_language_code(native_language)
    target_language = normalize_language_code(target_language)
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

        # Skip parts-missing warning for procedural paraphrase goals (we don't split them)
        skip_parts_warning = False
        if gl.language == native_language and "eng:procedural-paraphrase-expression-goal" in (gl.tags or []):
            skip_parts_warning = True

        if not skip_parts_warning and not (getattr(gl, "parts", None) or []) and not has_log(gl, SPLIT_LOG_MARKER):
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
            "display": paraphrase_display(gloss),
            "children": [],
            "marker": marker,
            "bold": parts_line and gloss.language == learn_lang,
            "role": role,
            "warn_native_missing": flags["warn_native_missing"],
            "warn_target_missing": flags["warn_target_missing"],
            "warn_usage_missing": flags["warn_usage_missing"],
            "warn_parts_missing": key in stats["parts_missing"],
            "state": determine_goal_state(gloss, storage, native_language, target_language)
            if role == "root"
            else "",
        }

        if key in path:
            return node
        next_path = set(path or [])
        next_path.add(key)

        if role in ("root", "part", "usage_part"):
            stats["glosses_to_learn"].add(key)

        is_procedural_root = (
            role == "root"
            and gloss.language == native_language
            and "eng:procedural-paraphrase-expression-goal" in (gloss.tags or [])
        )

        for part_ref in ([] if is_procedural_root else getattr(gloss, "parts", [])):
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
        goal_kind = detect_goal_type(gloss, native_language, target_language)
        marker = ""
        if goal_kind == "procedural":
            marker = "PROC "
            learn_lang = native_language
            goal_type = "procedural"
        elif goal_kind == "understanding":
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

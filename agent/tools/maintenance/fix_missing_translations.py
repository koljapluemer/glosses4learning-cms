"""Batch tool to resolve missing translations."""

from __future__ import annotations

import json
from typing import Annotated

from agents.run_context import RunContextWrapper
from agents.tool import function_tool

from agent.logging_config import LogContext
from agent.tools.database.add_translation import add_translation
from agent.tools.database.mark_untranslatable import mark_untranslatable
from agent.tools.llm.translate_native_glosses import translate_native_glosses
from agent.tools.llm.translate_paraphrased_native import translate_paraphrased_native
from agent.tools.llm.generate_translate_target_glosses import generate_translate_target_glosses
from agent.tools.queries.list_missing_translations import list_missing_translations


def _ensure_list(obj):
    if isinstance(obj, list):
        return obj
    return []


@function_tool
def fix_missing_translations(
    ctx: RunContextWrapper,
    situation_ref: Annotated[str | None, "Situation reference. If None, uses current situation."] = None,
) -> str:
    """
    Batch resolve missing translations for native, target, and paraphrased glosses.
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger
    native_language = agent_ctx.native_language
    target_language = agent_ctx.target_language

    if situation_ref is None:
        situation_ref = agent_ctx.situation_ref

    with LogContext(logger, tool="fix_missing_translations", situation_ref=situation_ref):
        try:
            missing_json = list_missing_translations(ctx, situation_ref=situation_ref, category="all")
            missing_data = json.loads(missing_json) if missing_json else {}
            native_missing = _ensure_list(missing_data.get("native_missing"))
            target_missing = _ensure_list(missing_data.get("target_missing"))
            paraphrased_missing = _ensure_list(missing_data.get("paraphrased_native_missing"))

            summary = {
                "native_translated": {},
                "target_translated": {},
                "paraphrase_translated": {},
                "marked_untranslatable": [],
                "errors": [],
            }

            # Paraphrased native goals -> target translations
            if paraphrased_missing:
                resp = translate_paraphrased_native(ctx, gloss_refs=paraphrased_missing)
                data = json.loads(resp) if resp else {}
                translations_map = data.get("translations", {}) if isinstance(data, dict) else {}
                for ref in paraphrased_missing:
                    items = translations_map.get(ref) or []
                    if items:
                        summary["paraphrase_translated"][ref] = []
                        for item in items:
                            if not isinstance(item, dict) or not item.get("text"):
                                continue
                            note = item.get("note", "")
                            add_translation(
                                ctx,
                                source_gloss_ref=ref,
                                translation_text=item["text"],
                                translation_language=target_language,
                                note_text=note,
                                note_language=native_language,
                            )
                            summary["paraphrase_translated"][ref].append(item)
                    else:
                        mark_untranslatable(ctx, gloss_ref=ref, target_language=target_language)
                        summary["marked_untranslatable"].append(ref)

            # Native glosses -> target translations
            if native_missing:
                resp = translate_native_glosses(ctx, gloss_refs=native_missing)
                data = json.loads(resp) if resp else {}
                translations_map = data.get("translations", {}) if isinstance(data, dict) else {}
                for ref in native_missing:
                    items = translations_map.get(ref) or []
                    if items:
                        summary["native_translated"][ref] = []
                        for item in items:
                            if not isinstance(item, dict) or not item.get("text"):
                                continue
                            note = item.get("note", "")
                            add_translation(
                                ctx,
                                source_gloss_ref=ref,
                                translation_text=item["text"],
                                translation_language=target_language,
                                note_text=note,
                                note_language=native_language,
                            )
                            summary["native_translated"][ref].append(item)
                    else:
                        mark_untranslatable(ctx, gloss_ref=ref, target_language=target_language)
                        summary["marked_untranslatable"].append(ref)

            # Target glosses -> native translations
            if target_missing:
                resp = generate_translate_target_glosses(ctx, gloss_refs=target_missing)
                try:
                    data = json.loads(resp) if resp else {}
                except json.JSONDecodeError as exc:
                    summary["errors"].append(f"Failed to parse target translations: {exc}")
                    data = {}
                translations_map = data if isinstance(data, dict) else {}
                for ref in target_missing:
                    items = translations_map.get(ref) or []
                    if items:
                        summary["target_translated"][ref] = []
                        for text in items:
                            if not isinstance(text, str) or not text.strip():
                                continue
                            add_translation(
                                ctx,
                                source_gloss_ref=ref,
                                translation_text=text.strip(),
                                translation_language=native_language,
                            )
                            summary["target_translated"][ref].append(text.strip())
                    else:
                        mark_untranslatable(ctx, gloss_ref=ref, target_language=native_language)
                        summary["marked_untranslatable"].append(ref)

            return json.dumps(summary, ensure_ascii=False, indent=2)
        except Exception as exc:  # noqa: BLE001
            error_msg = f"Failed to fix missing translations: {exc}"
            logger.error(error_msg, exc_info=True)
            return json.dumps({"error": error_msg})

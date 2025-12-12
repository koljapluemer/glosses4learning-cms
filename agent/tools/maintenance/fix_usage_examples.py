"""Batch tool to resolve missing usage examples."""

from __future__ import annotations

import json
from typing import Annotated, Iterable, List

from agents.run_context import RunContextWrapper
from agents.tool import function_tool

from agent.logging_config import LogContext
from agent.tools.database.add_usage_examples import add_usage_examples
from agent.tools.database.mark_no_usage_examples import mark_no_usage_examples
from agent.tools.llm.generate_usage_examples import generate_usage_examples
from agent.tools.llm.judge_usage_examples_useful import judge_usage_examples_useful
from agent.tools.queries.list_missing_usage import list_missing_usage
from src.shared.storage import Gloss, GlossStorage


def _chunk(seq: List[str], size: int) -> Iterable[list[str]]:
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def _parse_json_or_empty(payload: str):
    if not payload:
        return {}
    try:
        return json.loads(payload)
    except Exception:
        return {}


@function_tool
def fix_usage_examples(
    ctx: RunContextWrapper,
    situation_ref: Annotated[str | None, "Situation reference. If None, uses current situation."] = None,
    num_examples: Annotated[int, "Examples to generate per gloss"] = 3,
    judge_batch_size: Annotated[int, "How many glosses to judge per LLM call"] = 20,
) -> str:
    """
    Batch resolve missing usage examples:
    - List glosses missing usage
    - Judge if examples are appropriate
    - Generate example sentences where appropriate and attach them
    - Mark glosses as not needing usage examples when inappropriate
    """
    agent_ctx = ctx.context.get("agent_context")
    storage: GlossStorage = agent_ctx.storage
    logger = agent_ctx.logger

    if situation_ref is None:
        situation_ref = agent_ctx.situation_ref

    with LogContext(logger, tool="fix_usage_examples", situation_ref=situation_ref):
        try:
            missing_json = list_missing_usage(ctx, situation_ref=situation_ref)
            missing = _parse_json_or_empty(missing_json)
            gloss_entries = missing.get("glosses") or []
            gloss_refs = [g.get("ref") for g in gloss_entries if g.get("ref")]

            summary = {
                "judged": {},
                "added_examples": {},
                "marked_impossible": [],
                "errors": [],
            }

            if not gloss_refs:
                return json.dumps(summary, indent=2, ensure_ascii=False)

            # Judge in batches to avoid huge prompts
            judgments: dict[str, bool] = {}
            for batch in _chunk(gloss_refs, max(1, judge_batch_size)):
                resp = judge_usage_examples_useful(ctx, gloss_refs=batch)
                data = _parse_json_or_empty(resp)
                if isinstance(data, dict):
                    for ref, decision in data.items():
                        judgments[ref] = bool(decision)

            summary["judged"] = judgments

            for entry in gloss_entries:
                ref = entry.get("ref")
                if not ref:
                    continue
                gloss = storage.resolve_reference(ref)
                if not gloss:
                    summary["errors"].append(f"Gloss not found: {ref}")
                    continue

                allow_examples = judgments.get(ref, True)
                if not allow_examples:
                    mark_no_usage_examples(ctx, gloss_ref=ref, target_language=gloss.language)
                    summary["marked_impossible"].append(ref)
                    continue

                examples_resp = generate_usage_examples(ctx, gloss_ref=ref, num_examples=num_examples)
                examples_data = _parse_json_or_empty(examples_resp)
                examples = examples_data if isinstance(examples_data, list) else examples_data.get("examples", [])
                example_refs: list[str] = []
                for text in examples or []:
                    if not isinstance(text, str) or not text.strip():
                        continue
                    try:
                        example_gloss: Gloss = storage.ensure_gloss(gloss.language, text.strip())
                        example_refs.append(f"{example_gloss.language}:{example_gloss.slug}")
                    except Exception as exc:  # noqa: BLE001
                        summary["errors"].append(f"Failed to persist example for {ref}: {exc}")

                if example_refs:
                    add_usage_examples(ctx, gloss_ref=ref, example_refs=example_refs)
                    summary["added_examples"][ref] = example_refs
                else:
                    mark_no_usage_examples(ctx, gloss_ref=ref, target_language=gloss.language)
                    summary["marked_impossible"].append(ref)

            return json.dumps(summary, indent=2, ensure_ascii=False)
        except Exception as exc:  # noqa: BLE001
            error_msg = f"Failed to fix usage examples: {exc}"
            logger.error(error_msg, exc_info=True)
            return json.dumps({"error": error_msg})

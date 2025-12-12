"""Batch tool to resolve missing parts."""

from __future__ import annotations

import json
from typing import Annotated

from agents.run_context import RunContextWrapper
from agents.tool import function_tool

from agent.logging_config import LogContext
from agent.tools.database.add_parts import add_parts
from agent.tools.database.mark_unsplittable import mark_unsplittable
from agent.tools.llm.generate_split_gloss_parts import generate_split_gloss_parts
from agent.tools.llm.judge_glosses_splittable import judge_glosses_splittable
from agent.tools.queries.list_missing_parts import list_missing_parts


@function_tool
def fix_missing_parts(
    ctx: RunContextWrapper,
    situation_ref: Annotated[str | None, "Situation reference. If None, uses current situation."] = None,
) -> str:
    """
    Batch resolve glosses missing parts.

    Steps:
    1) Fetch missing parts list for the situation.
    2) Judge splittability; mark unsplittable where appropriate.
    3) For splittable glosses, generate parts and attach them.
    """
    agent_ctx = ctx.context.get("agent_context")
    logger = agent_ctx.logger

    if situation_ref is None:
        situation_ref = agent_ctx.situation_ref

    with LogContext(logger, tool="fix_missing_parts", situation_ref=situation_ref):
        try:
            missing_json = list_missing_parts(ctx, situation_ref=situation_ref)
            missing_data = json.loads(missing_json) if missing_json else {}
            glosses = missing_data.get("glosses", []) if isinstance(missing_data, dict) else []
            missing_refs = [g.get("ref") for g in glosses if g.get("ref")]

            if not missing_refs:
                return json.dumps({"message": "No glosses missing parts"})

            # Judge splittability in batches to avoid oversized prompts and parse errors
            def chunk(seq, size=20):
                for i in range(0, len(seq), size):
                    yield seq[i:i + size]

            judgment: dict[str, bool] = {}
            for batch in chunk(missing_refs, 20):
                judgment_json = judge_glosses_splittable(ctx, gloss_refs=batch)
                try:
                    parsed = json.loads(judgment_json) if judgment_json else {}
                except json.JSONDecodeError as exc:
                    errors.append(f"Failed to parse splittability judgment for batch {batch}: {exc}")
                    continue
                if isinstance(parsed, dict):
                    judgment.update(parsed)

            unsplittable = [ref for ref, val in judgment.items() if val is False]
            splittable = [ref for ref, val in judgment.items() if val is True]

            marked = []
            for ref in unsplittable:
                mark_unsplittable(ctx, gloss_ref=ref)
                marked.append(ref)

            added_parts = {}
            errors: list[str] = []

            for ref in splittable:
                parts_json = generate_split_gloss_parts(ctx, gloss_ref=ref)
                try:
                    parts = json.loads(parts_json) if parts_json else []
                except json.JSONDecodeError as exc:
                    errors.append(f"Failed to parse parts for {ref}: {exc}")
                    continue
                if isinstance(parts, list) and parts:
                    add_parts(ctx, gloss_ref=ref, part_refs=parts)
                    added_parts[ref] = parts
                else:
                    errors.append(f"No parts generated for {ref}")

            return json.dumps(
                {
                    "missing_count": len(missing_refs),
                    "marked_unsplittable": marked,
                    "split_success": added_parts,
                    "errors": errors,
                },
                ensure_ascii=False,
                indent=2,
            )
        except Exception as exc:  # noqa: BLE001
            error_msg = f"Failed to fix missing parts: {exc}"
            logger.error(error_msg, exc_info=True)
            return json.dumps({"error": error_msg})

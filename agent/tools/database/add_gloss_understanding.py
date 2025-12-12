"""Tool for adding understanding expression goals."""

from __future__ import annotations

from typing import Annotated

from agents import RunContextWrapper, function_tool

from agent.logging_config import LogContext
from src.shared.storage import Gloss, attach_relation

@function_tool
def add_gloss_as_understanding_goal(
    ctx: RunContextWrapper,
    content: Annotated[str, "Expression in target language to understand"],
    situation_ref: Annotated[str, "Situation reference to attach to (format: 'lang:slug')"],
) -> str:
    """
    Add a gloss as an understanding expression goal.

    Understanding goals are expressions or utterances in the target language
    that a learner might encounter and need to comprehend in the situation.

    Example: "Wo ist die Toilette?" (Where is the bathroom?)

    This tool:
    1. Creates/finds the gloss in target language
    2. Tags it with "eng:understand-expression-goal"
    3. Attaches it to the situation as a child

    Args:
        content: The target language expression to understand
        situation_ref: Reference to the situation to attach this goal to

    Returns:
        Success message with goal reference, or error message

    Example:
        add_gloss_as_understanding_goal(ctx, "Wo ist die Toilette?", "eng:at-the-airport")
        -> "Successfully added understanding goal. Reference: deu:Wo ist die Toilette?"
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger
    target_language = agent_ctx.target_language

    with LogContext(logger, tool="add_gloss_as_understanding_goal", situation_ref=situation_ref):
        logger.info(f"Adding understanding goal: '{content}'")

        try:
            # Load situation
            situation = storage.resolve_reference(situation_ref)
            if not situation:
                return f"Error: Situation not found: {situation_ref}"

            # Create or find the goal gloss
            existing = storage.find_gloss_by_content(target_language, content)

            if existing:
                goal_gloss = existing
                # Ensure tag is present
                tags = goal_gloss.tags or []
                if "eng:understand-expression-goal" not in tags:
                    tags.append("eng:understand-expression-goal")
                goal_gloss.tags = tags
                storage.save_gloss(goal_gloss)
            else:
                # Create new goal gloss
                goal_gloss = Gloss(
                    content=content,
                    language=target_language,
                    tags=["eng:understand-expression-goal"],
                )
                goal_gloss = storage.create_gloss(goal_gloss)

            goal_ref = f"{goal_gloss.language}:{goal_gloss.slug}"

            # Attach to situation
            attach_relation(storage, situation, "children", goal_gloss)

            logger.info(f"Successfully added understanding goal: {goal_ref}")
            return f"Successfully added understanding goal '{content}' to {situation_ref}. Reference: {goal_ref}"

        except Exception as e:
            error_msg = f"Failed to add understanding goal: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

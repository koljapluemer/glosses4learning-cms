"""Tool for adding procedural paraphrase expression goals."""

from __future__ import annotations

from typing import Annotated

from agents import RunContextWrapper, function_tool

from agent.logging_config import LogContext
from src.shared.storage import Gloss, attach_relation

@function_tool
def add_gloss_as_procedural_goal(
    ctx: RunContextWrapper,
    content: Annotated[str, "Procedural paraphrase expression in native language"],
    situation_ref: Annotated[str, "Situation reference to attach to (format: 'lang:slug')"],
) -> str:
    """
    Add a gloss as a procedural paraphrase expression goal.

    Procedural goals are communicative intents expressed in the learner's native
    language describing what they want to say in the target language.

    Example: "ask where something is", "express gratitude"

    This tool:
    1. Creates/finds the gloss in native language
    2. Tags it with "eng:paraphrase" and "eng:procedural-paraphrase-expression-goal"
    3. Attaches it to the situation as a child

    Args:
        content: The procedural description (e.g., "ask for directions")
        situation_ref: Reference to the situation to attach this goal to

    Returns:
        Success message with goal reference, or error message

    Example:
        add_gloss_as_procedural_goal(ctx, "ask where something is", "eng:at-the-airport")
        -> "Successfully added procedural goal. Reference: eng:ask where something is"
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger
    native_language = agent_ctx.native_language

    with LogContext(logger, tool="add_gloss_as_procedural_goal", situation_ref=situation_ref):
        logger.info(f"Adding procedural goal: '{content}'")

        try:
            # Load situation
            situation = storage.resolve_reference(situation_ref)
            if not situation:
                return f"Error: Situation not found: {situation_ref}"

            # Create or find the goal gloss
            existing = storage.find_gloss_by_content(native_language, content)

            if existing:
                goal_gloss = existing
                # Ensure tags are present
                tags = goal_gloss.tags or []
                if "eng:paraphrase" not in tags:
                    tags.append("eng:paraphrase")
                if "eng:procedural-paraphrase-expression-goal" not in tags:
                    tags.append("eng:procedural-paraphrase-expression-goal")
                goal_gloss.tags = tags
                storage.save_gloss(goal_gloss)
            else:
                # Create new goal gloss
                goal_gloss = Gloss(
                    content=content,
                    language=native_language,
                    tags=["eng:paraphrase", "eng:procedural-paraphrase-expression-goal"],
                )
                goal_gloss = storage.create_gloss(goal_gloss)

            goal_ref = f"{goal_gloss.language}:{goal_gloss.slug}"

            # Attach to situation
            attach_relation(storage, situation, "children", goal_gloss)

            logger.info(f"Successfully added procedural goal: {goal_ref}")
            return f"Successfully added procedural goal '{content}' to {situation_ref}. Reference: {goal_ref}"

        except Exception as e:
            error_msg = f"Failed to add procedural goal: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

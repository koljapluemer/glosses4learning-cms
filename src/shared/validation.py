"""Validation and judgment helpers for goal assessment."""

from __future__ import annotations

from src.shared.storage import Gloss, GlossStorage
from src.shared.tree import detect_goal_type, evaluate_goal_state


def get_goals_by_type(
    storage: GlossStorage,
    situation: Gloss,
    native_language: str,
    target_language: str,
    goal_type: str,  # "procedural" or "understanding"
) -> list[Gloss]:
    """
    Get all goals of a specific type from a situation.

    Filters the situation's children to find goals matching the specified type.
    Goal type is determined by tags and language:
    - "procedural": Native language goals tagged with "eng:procedural-paraphrase-expression-goal"
    - "understanding": Target language goals tagged with "eng:understand-expression-goal"

    Args:
        storage: GlossStorage instance
        situation: Situation gloss containing children goals
        native_language: Native language code
        target_language: Target language code
        goal_type: Either "procedural" or "understanding"

    Returns:
        List of goal glosses matching the specified type

    Example:
        >>> situation = storage.resolve_reference("eng:at-the-airport")
        >>> procedural = get_goals_by_type(storage, situation, "eng", "arb", "procedural")
        >>> understanding = get_goals_by_type(storage, situation, "eng", "arb", "understanding")
    """
    goals = []
    for ref in situation.children:
        gloss = storage.resolve_reference(ref)
        if not gloss:
            continue

        detected_type = detect_goal_type(gloss, native_language, target_language)
        if detected_type == goal_type:
            goals.append(gloss)

    return goals


def assess_goals_state(
    storage: GlossStorage,
    situation: Gloss,
    native_language: str,
    target_language: str,
) -> dict:
    """
    Assess the overall state of all goals in a situation.

    Evaluates each goal in the situation and categorizes them by their
    validation state (red/yellow/green). Also provides detailed logs
    explaining what's missing for each goal.

    States:
    - RED: Goal is missing critical requirements (translations, parts)
    - YELLOW: Goal meets minimum requirements, can be practiced
    - GREEN: Goal is complete with high-quality content

    Args:
        storage: GlossStorage instance
        situation: Situation gloss containing children goals
        native_language: Native language code
        target_language: Target language code

    Returns:
        Dict with:
        - red_goals: list of goal references in red state
        - yellow_goals: list of goal references in yellow state
        - green_goals: list of goal references in green state
        - detailed_logs: dict mapping goal_ref -> evaluation log string

    Example:
        >>> situation = storage.resolve_reference("eng:cooking-together")
        >>> assessment = assess_goals_state(storage, situation, "eng", "deu")
        >>> print(f"Red: {len(assessment['red_goals'])}, "
        ...       f"Yellow: {len(assessment['yellow_goals'])}, "
        ...       f"Green: {len(assessment['green_goals'])}")
        Red: 3, Yellow: 5, Green: 2
    """
    red_goals = []
    yellow_goals = []
    green_goals = []
    detailed_logs = {}

    for ref in situation.children:
        gloss = storage.resolve_reference(ref)
        if not gloss:
            continue

        # Skip non-goals
        if not detect_goal_type(gloss, native_language, target_language):
            continue

        # Evaluate goal state
        result = evaluate_goal_state(gloss, storage, native_language, target_language)
        state = result["state"]
        log = result["log"]

        goal_ref = f"{gloss.language}:{gloss.slug}"
        detailed_logs[goal_ref] = log

        # Categorize by state
        if state == "red":
            red_goals.append(goal_ref)
        elif state == "yellow":
            yellow_goals.append(goal_ref)
        else:  # green
            green_goals.append(goal_ref)

    return {
        "red_goals": red_goals,
        "yellow_goals": yellow_goals,
        "green_goals": green_goals,
        "detailed_logs": detailed_logs,
    }

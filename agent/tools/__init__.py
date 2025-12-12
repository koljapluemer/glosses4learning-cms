"""Tool registry for the agent system."""

from __future__ import annotations

# Database tools
from agent.tools.database.add_gloss import add_gloss, add_gloss_tool
from agent.tools.database.add_gloss_procedural import add_gloss_as_procedural_goal, add_gloss_as_procedural_goal_tool
from agent.tools.database.add_gloss_understanding import add_gloss_as_understanding_goal, add_gloss_as_understanding_goal_tool
from agent.tools.database.add_note import add_note, add_note_tool
from agent.tools.database.add_parts import add_parts, add_parts_tool
from agent.tools.database.add_translation import add_translation, add_translation_tool
from agent.tools.database.add_usage_examples import add_usage_examples, add_usage_examples_tool
from agent.tools.database.attach_to_situation import attach_to_situation, attach_to_situation_tool
from agent.tools.database.mark_no_usage_examples import mark_no_usage_examples, mark_no_usage_examples_tool
from agent.tools.database.mark_unsplittable import mark_unsplittable, mark_unsplittable_tool
from agent.tools.database.mark_untranslatable import mark_untranslatable, mark_untranslatable_tool

# Query tools
from agent.tools.queries.find_translation_siblings import find_translation_siblings, find_translation_siblings_tool
from agent.tools.queries.get_situation_state import get_situation_state, get_situation_state_tool
from agent.tools.queries.list_missing_parts import list_missing_parts, list_missing_parts_tool
from agent.tools.queries.list_missing_translations import list_missing_translations, list_missing_translations_tool
from agent.tools.queries.list_missing_usage import list_missing_usage, list_missing_usage_tool
from agent.tools.queries.list_procedural_goals import list_procedural_goals, list_procedural_goals_tool
from agent.tools.queries.list_understanding_goals import list_understanding_goals, list_understanding_goals_tool

# LLM tools
from agent.tools.llm.brainstorm_situation_ideas import brainstorm_situation_ideas, brainstorm_situation_ideas_tool
from agent.tools.llm.generate_procedural_goals import generate_procedural_goals, generate_procedural_goals_tool
from agent.tools.llm.generate_split_gloss_parts import generate_split_gloss_parts, generate_split_gloss_parts_tool
from agent.tools.llm.generate_translate_target_glosses import generate_translate_target_glosses, generate_translate_target_glosses_tool
from agent.tools.llm.generate_understanding_goals import generate_understanding_goals, generate_understanding_goals_tool
from agent.tools.llm.generate_usage_examples import generate_usage_examples, generate_usage_examples_tool
from agent.tools.llm.generate_usage_notes import generate_usage_notes, generate_usage_notes_tool
from agent.tools.llm.judge_expression_goals_coverage import judge_expression_goals_coverage, judge_expression_goals_coverage_tool
from agent.tools.llm.judge_glosses_splittable import judge_glosses_splittable, judge_glosses_splittable_tool
from agent.tools.llm.judge_understanding_goals_coverage import judge_understanding_goals_coverage, judge_understanding_goals_coverage_tool
from agent.tools.llm.judge_usage_examples_useful import judge_usage_examples_useful, judge_usage_examples_useful_tool
from agent.tools.llm.translate_native_glosses import translate_native_glosses, translate_native_glosses_tool
from agent.tools.llm.translate_paraphrased_native import translate_paraphrased_native, translate_paraphrased_native_tool


def get_all_tools() -> list:
    """
    Get all available tools for the agent.

    Returns a list of all tool functions that can be registered with the agent.
    Tools are grouped by type: database operations, queries, and LLM-powered tools.

    Returns:
        List of tool functions
    """
    return [
        # Database tools (11)
        add_gloss,
        add_gloss_as_procedural_goal,
        add_gloss_as_understanding_goal,
        add_translation,
        add_parts,
        add_usage_examples,
        add_note,
        mark_unsplittable,
        mark_untranslatable,
        mark_no_usage_examples,
        attach_to_situation,
        # Query tools (7)
        get_situation_state,
        list_procedural_goals,
        list_understanding_goals,
        list_missing_translations,
        list_missing_parts,
        list_missing_usage,
        find_translation_siblings,
        # LLM tools (13 - ALL IMPLEMENTED)
        generate_procedural_goals,
        generate_understanding_goals,
        translate_paraphrased_native,
        translate_native_glosses,
        judge_usage_examples_useful,
        generate_usage_examples,
        judge_glosses_splittable,
        generate_split_gloss_parts,
        generate_translate_target_glosses,
        generate_usage_notes,
        judge_expression_goals_coverage,
        judge_understanding_goals_coverage,
        brainstorm_situation_ideas,
    ]


def get_all_tool_wrappers() -> list:
    """
    Return the FunctionTool wrappers (from openai-agents) for all tools.
    These are the objects to hand to the Agents SDK.
    """
    return [
        # Database wrappers
        add_gloss_tool,
        add_gloss_as_procedural_goal_tool,
        add_gloss_as_understanding_goal_tool,
        add_translation_tool,
        add_parts_tool,
        add_usage_examples_tool,
        add_note_tool,
        mark_unsplittable_tool,
        mark_untranslatable_tool,
        mark_no_usage_examples_tool,
        attach_to_situation_tool,
        # Query wrappers
        get_situation_state_tool,
        list_procedural_goals_tool,
        list_understanding_goals_tool,
        list_missing_translations_tool,
        list_missing_parts_tool,
        list_missing_usage_tool,
        find_translation_siblings_tool,
        # LLM wrappers
        generate_procedural_goals_tool,
        generate_understanding_goals_tool,
        translate_paraphrased_native_tool,
        translate_native_glosses_tool,
        judge_usage_examples_useful_tool,
        generate_usage_examples_tool,
        judge_glosses_splittable_tool,
        generate_split_gloss_parts_tool,
        generate_translate_target_glosses_tool,
        generate_usage_notes_tool,
        judge_expression_goals_coverage_tool,
        judge_understanding_goals_coverage_tool,
        brainstorm_situation_ideas_tool,
    ]


__all__ = [
    "get_all_tools",
    # Database tools
    "add_gloss",
    "add_gloss_as_procedural_goal",
    "add_gloss_as_understanding_goal",
    "add_translation",
    "add_parts",
    "add_usage_examples",
    "add_note",
    "mark_unsplittable",
    "mark_untranslatable",
    "mark_no_usage_examples",
    "attach_to_situation",
    # Query tools
    "get_situation_state",
    "list_procedural_goals",
    "list_understanding_goals",
    "list_missing_translations",
    "list_missing_parts",
    "list_missing_usage",
    "find_translation_siblings",
    # LLM tools
    "generate_procedural_goals",
    "generate_understanding_goals",
    "translate_paraphrased_native",
    "translate_native_glosses",
    "judge_usage_examples_useful",
    "generate_usage_examples",
    "judge_glosses_splittable",
    "generate_split_gloss_parts",
    "generate_translate_target_glosses",
    "generate_usage_notes",
    "judge_expression_goals_coverage",
    "judge_understanding_goals_coverage",
    "brainstorm_situation_ideas",
    "get_all_tool_wrappers",
]

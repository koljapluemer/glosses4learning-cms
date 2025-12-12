"""Tool for brainstorming ideas about a learning situation."""

from __future__ import annotations

from typing import Annotated

from agents import RunContextWrapper, function_tool

from agent.logging_config import LogContext
from src.shared.languages import get_ai_note
from src.shared.llm_client import get_openai_client

# Configuration constants
MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0.6

SYSTEM_PROMPT = """You brainstorm ideas for language learning situations.

Generate creative, practical ideas about dialogs, conversations, utterances, and expression desires a learner might encounter."""

USER_PROMPT_TEMPLATE = """Situation: {situation_description}

{context_text}

Brainstorm ideas about:
- What kinds of dialogs or conversations might occur
- What utterances the learner might hear
- What the learner might want to express
- Common interactions or exchanges

{ai_note}

Provide your brainstorming as free-form text with practical, realistic ideas."""


@function_tool
def brainstorm_situation_ideas(
    ctx: RunContextWrapper,
    situation_ref: Annotated[str, "Situation reference (format: 'lang:slug')"],
    additional_context: Annotated[str | None, "Optional additional context or constraints"] = None,
) -> str:
    """
    Brainstorm ideas about dialogs, conversations, and utterances for a situation.

    Generates creative ideas about what kinds of interactions, dialogs, conversations,
    and expression desires a learner might encounter in the given situation.

    Args:
        situation_ref: Reference to the situation to brainstorm about
        additional_context: Optional additional context or specific focus areas

    Returns:
        Free-form text with brainstormed ideas, or error message

    Example:
        brainstorm_situation_ideas(ctx, "eng:at-restaurant")
        -> "In a restaurant, learners might need to: ask for a table, order food..."
    """
    agent_ctx = ctx.context.get("agent_context")
    storage = agent_ctx.storage
    logger = agent_ctx.logger
    api_key = agent_ctx.api_key
    target_language = agent_ctx.target_language

    with LogContext(logger, tool="brainstorm_situation_ideas", situation_ref=situation_ref):
        logger.info(f"Brainstorming ideas for {situation_ref}")

        try:
            # Load situation
            situation = storage.resolve_reference(situation_ref)
            if not situation:
                error_msg = f"Situation not found: {situation_ref}"
                logger.error(error_msg)
                return f"Error: {error_msg}"

            # Get language AI note for target language
            ai_note = get_ai_note(target_language)
            ai_note_text = f"Language/cultural notes for {target_language}: {ai_note}" if ai_note else ""

            # Build context text
            context_text = f"Additional context: {additional_context}" if additional_context else ""

            # Build prompt
            prompt = USER_PROMPT_TEMPLATE.format(
                situation_description=situation.content,
                context_text=context_text,
                ai_note=ai_note_text,
            )

            # Call LLM (no structured response - free-form text)
            client = get_openai_client(api_key)
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=TEMPERATURE,
                max_tokens=800,
            )

            ideas = response.choices[0].message.content.strip()

            if not ideas:
                logger.warning(f"No ideas generated for {situation_ref}")
                return "No ideas generated."

            logger.info(f"Generated {len(ideas)} characters of brainstorming")
            return ideas

        except Exception as e:
            error_msg = f"Failed to brainstorm situation ideas: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

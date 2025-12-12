"""Main agent orchestration for autonomous situation filling."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from agent.config import DATA_ROOT, DEFAULT_AGENT_MODEL, DEFAULT_MAX_ITERATIONS
from agent.context import AgentContext
from agent.logging_config import setup_agent_logging
from src.shared.llm_client import get_openai_client
from src.shared.state import load_state, save_state
from src.shared.storage import GlossStorage


# System instructions for the agent
SYSTEM_INSTRUCTIONS = """You are an autonomous language learning content creation agent.

Your goal: Fill the learning situation with rich content until it is "well covered" (all goals are GREEN).

Process:
1. First, check the situation state using get_situation_state
2. Analyze what's missing (red/yellow goals, missing translations, parts, usage examples)
3. Prioritize completing red → yellow → green progressively
4. Use generation tools to create content
5. Review generated content and add appropriate items
6. Continuously re-check state and address gaps
7. When all goals are green and coverage is excellent, you're done

Guidelines:
- Work systematically: fix red goals before perfecting yellow ones
- Generate multiple options and select quality content
- Add translations, parts, and usage examples as needed
- Use judgment tools to avoid unnecessary work
- Provide clear reasoning for your decisions
- Always recheck state after major changes

When glosses already exist in storage, the tools will handle reuse automatically.
Be thorough but efficient - aim for high-quality, well-connected content.

IMPORTANT: You can call multiple tools in sequence. After generating content (like goals or translations),
review the results and call the appropriate database tools to add the desired items."""


def create_tool_schemas_for_openai(tools: list) -> list[dict]:
    """
    Create OpenAI function schemas from tool functions.

    This is a simplified version that extracts function metadata.
    In a full implementation, this would parse the @function_tool decorators.

    For now, we'll create a basic mapping manually for the implemented tools.
    """
    # Manual tool schemas for the implemented tools
    # In production, these would be auto-generated from tool decorators
    tool_schemas = [
        {
            "type": "function",
            "function": {
                "name": "get_situation_state",
                "description": "Get comprehensive state information about the learning situation including goal validation states",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "situation_ref": {
                            "type": "string",
                            "description": "Situation reference (format: 'lang:slug'). If null, uses current situation from context."
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "generate_procedural_goals",
                "description": "Generate procedural paraphrase expression goals for a situation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "situation_ref": {"type": "string", "description": "Situation reference"},
                        "num_goals": {"type": "integer", "description": "Number of goals to generate", "default": 5},
                        "extra_context": {"type": "string", "description": "Optional extra context"}
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "add_gloss_as_procedural_goal",
                "description": "Add a gloss as a procedural paraphrase expression goal to the situation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Procedural paraphrase expression in native language"},
                        "situation_ref": {"type": "string", "description": "Situation reference"}
                    },
                    "required": ["content", "situation_ref"]
                }
            }
        },
    ]

    return tool_schemas


def run_agent_simple(
    storage: GlossStorage,
    api_key: str,
    situation_ref: str,
    native_language: str,
    target_language: str,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    session_id: str | None = None,
) -> dict:
    """
    Run a simple agent loop without external SDK dependencies.

    This is a minimal viable implementation that:
    1. Checks situation state
    2. Provides recommendations
    3. Allows manual next steps

    For full autonomous operation, integrate with OpenAI Assistants API or similar.
    """
    session_id = session_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    logger = setup_agent_logging(session_id)

    # Create agent context
    agent_ctx = AgentContext(
        storage=storage,
        state={
            "situation_ref": situation_ref,
            "native_language": native_language,
            "target_language": target_language,
        },
        api_key=api_key,
        logger=logger,
    )

    logger.info(f"Agent started. Session: {session_id}")
    logger.info(f"Situation: {situation_ref}, Languages: {native_language} → {target_language}")

    # Import tools
    from agent.tools.queries.get_situation_state import get_situation_state

    # Create a simple context wrapper for tools
    class SimpleContext:
        def __init__(self, agent_context):
            self.context = {"agent_context": agent_context}

    ctx = SimpleContext(agent_ctx)

    # Get initial state
    logger.info("Checking initial situation state...")
    state_json = get_situation_state(ctx, situation_ref=None)
    state = json.loads(state_json)

    logger.info(f"Initial state: {state.get('summary')}")
    print(f"\n{'='*60}")
    print(f"AGENT SESSION: {session_id}")
    print(f"{'='*60}")
    print(f"\nSituation: {situation_ref}")
    print(f"Languages: {native_language} → {target_language}")
    print(f"\n{state.get('summary')}")
    print(f"\nTotal goals: {state.get('total_goals')}")
    print(f"  Red: {state.get('red_goals')}")
    print(f"  Yellow: {state.get('yellow_goals')}")
    print(f"  Green: {state.get('green_goals')}")

    # Provide next steps recommendations
    print(f"\n{'='*60}")
    print("RECOMMENDED NEXT STEPS:")
    print(f"{'='*60}")

    if state.get('total_goals') == 0:
        print("\n1. Generate procedural goals using generate_procedural_goals tool")
        print("2. Generate understanding goals using generate_understanding_goals tool")
        print("3. Add generated goals using add_gloss_as_procedural_goal and add_gloss_as_understanding_goal")
    elif state.get('red_goals', 0) > 0:
        print(f"\n{state.get('red_goals')} RED goals need attention:")
        print("1. Check list_missing_translations to see what needs translating")
        print("2. Use translate_paraphrased_native or translate_native_glosses to generate translations")
        print("3. Add translations using add_translation tool")
        print("4. Check list_missing_parts for glosses that need splitting")
    elif state.get('yellow_goals', 0) > 0:
        print(f"\n{state.get('yellow_goals')} YELLOW goals can be improved:")
        print("1. Add more translations for better coverage")
        print("2. Add usage examples for target language glosses")
        print("3. Add notes to translation siblings")
    else:
        print("\n✓ All goals are GREEN! Situation is well covered.")

    print(f"\n{'='*60}")
    print(f"Session logs: agent/logs/agent_session_{session_id}.log")
    print(f"{'='*60}\n")

    logger.info("Agent session completed")

    return {
        "success": True,
        "session_id": session_id,
        "initial_state": state,
        "message": "Simple agent inspection complete. See logs and use tools manually for now.",
    }


def run_agent_for_situation(
    situation_ref: str,
    native_language: str,
    target_language: str,
    api_key: str | None = None,
    data_root: Path | None = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> dict:
    """
    Convenience function to run agent for a situation.

    Args:
        situation_ref: Situation reference (e.g., "eng:cooking-together")
        native_language: Native language code (e.g., "eng")
        target_language: Target language code (e.g., "deu")
        api_key: OpenAI API key (defaults to state)
        data_root: Data root path (defaults to project root)
        max_iterations: Maximum agent iterations

    Returns:
        Dict with run statistics
    """
    # Load state for API key if not provided
    if not api_key:
        state = load_state()
        api_key = state.get("settings", {}).get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("API key required (not found in state)")

    # Setup storage
    if not data_root:
        data_root = DATA_ROOT

    storage = GlossStorage(data_root=data_root)

    # Update state
    state = load_state()
    state["situation_ref"] = situation_ref
    state["native_language"] = native_language
    state["target_language"] = target_language
    save_state(state)

    # Run agent
    return run_agent_simple(
        storage=storage,
        api_key=api_key,
        situation_ref=situation_ref,
        native_language=native_language,
        target_language=target_language,
        max_iterations=max_iterations,
    )

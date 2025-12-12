"""Main agent orchestration for autonomous situation filling."""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

from agents.agent import Agent
from agents.model_settings import ModelSettings
from agents.run import Runner

from agent.config import DATA_ROOT, DEFAULT_AGENT_MODEL, DEFAULT_MAX_ITERATIONS
from agent.context import AgentContext
from agent.logging_config import setup_agent_logging
from agent.tools import get_all_tool_wrappers
from openai import RateLimitError
from src.shared.state import get_api_key, load_state, save_state
from src.shared.storage import Gloss, GlossStorage


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

# When situations are empty, the agent should bootstrap coverage:
# - Brainstorm ideas for the situation
# - Generate procedural (things to say) and understanding (things to hear) goals
# - Add them, then re-check coverage using the coverage judgment tools


def create_tool_schemas_for_openai(tools: list | None = None) -> list[dict]:
    """
    Create OpenAI function schemas from tool functions.

    This uses the FunctionTool wrappers from the OpenAI Agents SDK, so the
    parameter schemas stay in sync with the tool signatures.
    """
    if tools is None:
        tools = get_all_tool_wrappers()

    schemas: list[dict] = []
    for tool in tools:
        name = getattr(tool, "name", None) or str(tool)
        desc = getattr(tool, "description", "") or ""
        params = getattr(tool, "params_json_schema", {"type": "object", "properties": {}, "required": []})
        schemas.append({
            "type": "function",
            "function": {
                "name": name,
                "description": desc,
                "parameters": params,
            }
        })
    return schemas


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

    # Import tools (full registry available via get_all_tool_wrappers)
    all_tool_wrappers = get_all_tool_wrappers()
    logger.info(f"Loaded {len(all_tool_wrappers)} tools for agent use.")
    from agent.tools.queries.get_situation_state import get_situation_state
    from agent.tools.llm.brainstorm_situation_ideas import brainstorm_situation_ideas
    from agent.tools.llm.generate_procedural_goals import generate_procedural_goals
    from agent.tools.llm.generate_understanding_goals import generate_understanding_goals
    from agent.tools.llm.judge_expression_goals_coverage import judge_expression_goals_coverage
    from agent.tools.llm.judge_understanding_goals_coverage import judge_understanding_goals_coverage
    from agent.tools.database.add_gloss_procedural import add_gloss_as_procedural_goal
    from agent.tools.database.add_gloss_understanding import add_gloss_as_understanding_goal
    from src.shared.tree import detect_goal_type

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
    # Build an Agents SDK agent and let it run with the full toolset
    all_tool_wrappers = get_all_tool_wrappers()
    logger.info(f"Loaded {len(all_tool_wrappers)} tools for agent use.")

    def _instructions(context, _agent):
        ctx = getattr(context, "context", {}) or {}
        agent_context = ctx.get("agent_context")
        return (
            f"{SYSTEM_INSTRUCTIONS}\n\n"
            f"Situation: {getattr(agent_context, 'situation_ref', situation_ref)}\n"
            f"Native→Target: {getattr(agent_context, 'native_language', native_language)} → {getattr(agent_context, 'target_language', target_language)}\n"
            "- If no goals exist, brainstorm the situation, generate procedural and understanding goals (5–8 each), add them, and re-check coverage. "
            "Stop after two generation passes or when coverage judges are >=7/10.\n"
            "- Skip duplicate/empty goals; ignore tool responses containing errors.\n"
            "- Log each step (brainstorm, generate counts, judge scores) concisely.\n"
        )

    agent = Agent(
        name="SituationFiller",
        instructions=_instructions,
        model=DEFAULT_AGENT_MODEL,
        model_settings=ModelSettings(tool_choice="auto"),
        tools=all_tool_wrappers,
    )

    # Use the initial state as input context for the agent
    initial_prompt = (
        "Current situation state (JSON):\n"
        f"{state_json}\n\n"
        "Improve coverage until goals are well covered. Act using the available tools."
    )

    def _retry_delay_seconds(exc: RateLimitError, fallback: float) -> float:
        # Extract "try again in Xs" if present; otherwise use fallback.
        msg = str(exc)
        match = re.search(r"try again in ([0-9]+(?:\\.[0-9]+)?)s", msg)
        if match:
            try:
                return max(fallback, float(match.group(1)))
            except Exception:
                return fallback
        return fallback

    result = None
    max_attempts = 5
    delay = 2.0
    for attempt in range(1, max_attempts + 1):
        try:
            result = Runner.run_sync(
                agent,
                initial_prompt,
                context={"agent_context": agent_ctx},
                max_turns=max_iterations,
            )
            break
        except RateLimitError as e:
            wait = _retry_delay_seconds(e, delay)
            logger.warning(
                "Rate limit hit (attempt %d/%d). Waiting %.2fs then retrying. Error: %s",
                attempt,
                max_attempts,
                wait,
                e,
            )
            time.sleep(wait)
            delay = min(delay * 2, 30.0)
            continue
    if result is None:
        return {
            "success": False,
            "session_id": session_id,
            "error": "Rate limit exceeded after retries; please try again later.",
        }

    final_output = getattr(result, "final_output", None)
    print(f"\n{'='*60}")
    print("FINAL OUTPUT")
    print(f"{'='*60}")
    print(final_output or "(no final output)")
    print(f"\nSession logs: agent/logs/agent_session_{session_id}.log\n")

    logger.info("Agent session completed")

    return {
        "success": True,
        "session_id": session_id,
        "initial_state": state,
        "message": final_output or "Agent run complete.",
    }


def run_agent_for_situation(
    situation_ref: str,
    native_language: str,
    target_language: str,
    data_root: Path | None = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> dict:
    """
    Convenience function to run agent for a situation.

    Args:
        situation_ref: Situation reference (e.g., "eng:cooking-together")
        native_language: Native language code (e.g., "eng")
        target_language: Target language code (e.g., "deu")
        data_root: Data root path (defaults to project root)
        max_iterations: Maximum agent iterations

    Returns:
        Dict with run statistics
    """
    # Always load API key from local state file
    api_key = get_api_key()
    os.environ["OPENAI_API_KEY"] = api_key

    # Setup storage
    if not data_root:
        data_root = DATA_ROOT

    storage = GlossStorage(data_root=data_root)

    def _ensure_situation_exists(ref: str) -> str:
        """
        Situations are always stored under language 'eng' regardless of native/target.
        Normalize the reference and create a bare situation gloss if missing.
        """
        slug = ref.split(":", 1)[1] if ":" in ref else ref
        slug = slug.strip()
        if not slug:
            raise ValueError("Situation reference must include a slug")
        canonical_ref = f"eng:{slug}"
        existing = storage.resolve_reference(canonical_ref)
        if existing:
            return canonical_ref
        situation_gloss = Gloss(content=slug, language="eng")
        storage.create_gloss(situation_gloss)
        return canonical_ref

    canonical_situation_ref = _ensure_situation_exists(situation_ref)

    # Update state
    state = load_state()
    state["situation_ref"] = canonical_situation_ref
    state["native_language"] = native_language
    state["target_language"] = target_language
    save_state(state)

    # Run agent
    return run_agent_simple(
        storage=storage,
        api_key=api_key,
        situation_ref=canonical_situation_ref,
        native_language=native_language,
        target_language=target_language,
        max_iterations=max_iterations,
    )

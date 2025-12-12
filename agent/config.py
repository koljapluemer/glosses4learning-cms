"""Global configuration constants for the agent system."""

from __future__ import annotations

from pathlib import Path

# Project root directory
REPO_ROOT = Path(__file__).resolve().parents[1]

# Data directory
DATA_ROOT = REPO_ROOT / "data"

# Agent logs directory
AGENT_LOG_DIR = Path(__file__).parent / "logs"

# Agent configuration
DEFAULT_MAX_ITERATIONS = 50
DEFAULT_AGENT_MODEL = "gpt-4o"  # Main reasoning model
DEFAULT_TOOL_LLM_MODEL = "gpt-4o-mini"  # For individual tool LLM calls

# Temperature defaults for different tool types
TEMPERATURE_CREATIVE = 0.7  # For goal generation, brainstorming
TEMPERATURE_TRANSLATION = 0.2  # For translations, splitting
TEMPERATURE_JUDGMENT = 0.0  # For yes/no judgments, ratings

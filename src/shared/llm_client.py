"""Shared OpenAI client wrapper for consistent LLM access."""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def get_openai_client(api_key: str):
    """
    Get cached OpenAI client instance.

    Uses functools.lru_cache to ensure we reuse the same client instance
    for a given API key, avoiding repeated initialization overhead.

    Args:
        api_key: OpenAI API key

    Returns:
        OpenAI client instance

    Raises:
        RuntimeError: If openai package is not installed
    """
    try:
        from openai import OpenAI
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Install openai package: pip install openai") from exc
    return OpenAI(api_key=api_key)

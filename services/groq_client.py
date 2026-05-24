"""Backward-compatible re-exports — prefer `from services.llm_client import llm_client`."""
from services.llm_client import (  # noqa: F401
    GroqClient,
    OllamaClient,
    check_ollama_reachable,
    groq_client,
    llm_client,
    _strip_json_fences,
)

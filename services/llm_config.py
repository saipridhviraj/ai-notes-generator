"""LLM provider selection — flip one env var to switch Groq ↔ Ollama."""
import os


def use_ollama() -> bool:
    """Return True when the app should call a local Ollama server."""
    flag = os.getenv("USE_OLLAMA", "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return True
    provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()
    return provider == "ollama"


def get_provider_name() -> str:
    return "ollama" if use_ollama() else "groq"

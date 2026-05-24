"""Prompt profile selection — dev (Groq free tier) vs production (full quality)."""
import os

from services.llm_config import use_ollama


def _ollama_num_ctx() -> int:
    return int(os.getenv("OLLAMA_NUM_CTX", "8192"))


def use_production_prompts() -> bool:
    """
    Return True when full production prompts and token limits should be used.

    Priority:
    1. USE_PRODUCTION_PROMPTS=true|false (explicit override)
    2. PROMPT_PROFILE=production|dev
    3. Auto: Ollama → production, Groq → dev
    """
    explicit = os.getenv("USE_PRODUCTION_PROMPTS", "").strip().lower()
    if explicit in ("1", "true", "yes", "on"):
        return True
    if explicit in ("0", "false", "no", "off"):
        return False

    profile = os.getenv("PROMPT_PROFILE", "").strip().lower()
    if profile == "production":
        return True
    if profile == "dev":
        return False

    return use_ollama()


def get_prompt_profile() -> str:
    return "production" if use_production_prompts() else "dev"


def is_fast_local_mode() -> bool:
    """Speed profile for local Ollama — smaller prompts, fewer tokens, supplement tutor."""
    if not use_ollama():
        return False
    flag = os.getenv("OLLAMA_FAST_MODE", "true").strip().lower()
    return flag in ("1", "true", "yes", "on", "")


def is_two_minute_mode() -> bool:
    """Aggressive caps targeting ~2 min/topic on local Ollama (after plan approval)."""
    if not use_ollama():
        return False
    flag = os.getenv("OLLAMA_2MIN_MODE", "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return True
    target = os.getenv("OLLAMA_TARGET_MINUTES", "").strip()
    return target == "2"


def use_fast_eval_heuristic() -> bool:
    """True when EVAL_MODE=heuristic (no evaluator LLM)."""
    return get_eval_mode() == "heuristic"


def get_eval_mode() -> str:
    """
    Evaluator strategy: heuristic | light | full.

    - heuristic: Python-only (~1s)
    - light: structural summary + small LLM JSON (default on Ollama)
    - full: entire notes in prompt (Groq / explicit)
    """
    explicit = os.getenv("FAST_EVAL_HEURISTIC", "").strip().lower()
    if explicit in ("1", "true", "yes", "on"):
        return "heuristic"

    mode = os.getenv("EVAL_MODE", "").strip().lower()
    if mode in ("heuristic", "light", "full"):
        return mode

    if explicit in ("0", "false", "no", "off"):
        return "light" if use_ollama() else "full"

    if is_two_minute_mode():
        return "heuristic"
    if use_ollama():
        return "light"
    return "full"


def get_eval_max_tokens() -> int:
    if get_eval_mode() == "light":
        return int(os.getenv("EVAL_MAX_TOKENS", "384"))
    return int(os.getenv("EVAL_MAX_TOKENS", "2048"))


def get_eval_llm_size() -> str:
    return "small" if get_eval_mode() == "light" else "reasoning"


def use_tutor_supplement_mode() -> bool:
    """Tutor writes annotation blocks only; Python merges into student notes."""
    explicit = os.getenv("TUTOR_SUPPLEMENT_MODE", "").strip().lower()
    if explicit in ("1", "true", "yes", "on"):
        return True
    if explicit in ("0", "false", "no", "off"):
        return False
    return is_fast_local_mode()


def get_few_shot_max_chars() -> int | None:
    explicit = os.getenv("FEW_SHOT_MAX_CHARS", "").strip()
    if explicit:
        if explicit.lower() in ("0", "none", "off", "false", "full"):
            return None
        return int(explicit)
    if is_two_minute_mode():
        return 2000
    if is_fast_local_mode():
        return 4500
    # Local 9B + 8K context: full Day-1 example (~21KB) will not fit with output tokens
    if use_ollama() and _ollama_num_ctx() <= 8192:
        return 4500
    return None


def get_note_max_tokens() -> int:
    if use_ollama():
        if is_two_minute_mode():
            return int(os.getenv("OLLAMA_NOTE_MAX_TOKENS", "2048"))
        return int(os.getenv("OLLAMA_NOTE_MAX_TOKENS", "4096"))
    if use_production_prompts():
        return int(os.getenv("PRODUCTION_NOTE_MAX_TOKENS", "8192"))
    return int(os.getenv("DEV_NOTE_MAX_TOKENS", "2048"))


def get_tutor_max_tokens() -> int:
    if use_tutor_supplement_mode():
        if is_two_minute_mode():
            return int(os.getenv("TUTOR_SUPPLEMENT_MAX_TOKENS", "768"))
        return int(os.getenv("TUTOR_SUPPLEMENT_MAX_TOKENS", "4096"))
    return get_note_max_tokens()


def get_tutor_handoff_max_sections() -> int:
    """Cap H2 sections sent to tutor JSON — avoids truncated responses on long lessons."""
    if is_two_minute_mode():
        return int(os.getenv("TUTOR_HANDOFF_MAX_SECTIONS", "6"))
    return int(os.getenv("TUTOR_HANDOFF_MAX_SECTIONS", "10"))


def get_mermaid_supplement_max_tokens() -> int:
    return int(os.getenv("MERMAID_SUPPLEMENT_MAX_TOKENS", "3072"))


def get_mermaid_max_retries() -> int:
    """Repair passes after initial validation (default 2 → 3 total attempts)."""
    return int(os.getenv("MERMAID_MAX_RETRIES", "2"))


def get_mermaid_llm_temperature() -> float:
    """Low temperature for structured diagram generation (default 0)."""
    return float(os.getenv("MERMAID_LLM_TEMPERATURE", "0"))


def get_mermaid_llm_ollama_options() -> dict:
    """Extra Ollama sampling options for Mermaid calls."""
    return {
        "top_p": float(os.getenv("MERMAID_LLM_TOP_P", "0.9")),
        "repeat_penalty": float(os.getenv("MERMAID_LLM_REPEAT_PENALTY", "1.1")),
    }


def get_mermaid_generation_mode() -> str:
    """
    How supplement/repair diagrams are generated.
    - json: LLM outputs diagram JSON → Python compiles to Mermaid (recommended for local 9B)
    - mermaid: LLM outputs Mermaid syntax directly (legacy)
    """
    mode = os.getenv("MERMAID_GENERATION_MODE", "json").strip().lower()
    return mode if mode in ("json", "mermaid") else "json"


def get_research_max_tokens() -> int:
    if is_two_minute_mode():
        return int(os.getenv("RESEARCH_MAX_TOKENS", "512"))
    if is_fast_local_mode():
        return int(os.getenv("RESEARCH_MAX_TOKENS", "1024"))
    return int(os.getenv("RESEARCH_MAX_TOKENS", "2048"))


def get_section_preview_chars() -> int:
    if is_two_minute_mode():
        return int(os.getenv("SECTION_PREVIEW_CHARS", "160"))
    return int(os.getenv("SECTION_PREVIEW_CHARS", "320"))


def get_gap_max_tokens() -> int:
    return int(os.getenv("GAP_MAX_TOKENS", "2048"))


def get_eval_snippet_chars() -> int | None:
    if is_fast_local_mode():
        return int(os.getenv("EVAL_SNIPPET_CHARS", "3500"))
    return None


def use_diagram_pipeline() -> bool:
    """
    When true: student notes use <!-- diagram --> placeholders;
    diagram_generator produces JSON + SVG embeds (no Mermaid in notes).
    Default is false — use inline ```mermaid``` blocks (recommended for Qwen/local models).
    Set DIAGRAM_PIPELINE=true to enable the JSON/SVG/React Flow pipeline.
    """
    flag = os.getenv("DIAGRAM_PIPELINE", "false").strip().lower()
    return flag in ("1", "true", "yes", "on")


def get_min_diagrams() -> int:
    """Minimum diagram count (placeholders or Mermaid blocks depending on pipeline mode)."""
    return get_min_mermaid_diagrams()


def get_min_mermaid_diagrams() -> int:
    if is_fast_local_mode():
        return int(os.getenv("MIN_MERMAID_DIAGRAMS", "2"))
    if use_production_prompts():
        return int(os.getenv("MIN_MERMAID_DIAGRAMS", "4"))
    return int(os.getenv("MIN_MERMAID_DIAGRAMS", "2"))

"""Strip pipeline wrapper prose from Mermaid supplement/repair LLM output."""

from __future__ import annotations

import re

_AFTER_MARKER = re.compile(
    r"<!--\s*after:\s*(.+?)\s*-->\s*\n(.*?)(?=<!--\s*after:|<!--\s*replace:|$)",
    re.DOTALL | re.IGNORECASE,
)
_REPLACE_MARKER = re.compile(
    r"<!--\s*replace:\s*(\d+)\s*-->\s*\n(.*?)(?=<!--\s*after:|<!--\s*replace:|$)",
    re.DOTALL | re.IGNORECASE,
)
_MERMAID_FENCE = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)
_WRAPPER_ONLY_LINE = re.compile(
    r"^\s*(Topic:|Context:|Insert after:|Return:|TASK:|SUPPLEMENT WRAPPER|REPAIR WRAPPER)\b",
    re.IGNORECASE | re.MULTILINE,
)


def _extract_mermaid_only(block: str) -> str:
    """From a marker block, keep only ```mermaid fences (drop echoed lesson prose)."""
    fences = _MERMAID_FENCE.findall(block or "")
    if not fences:
        return ""
    return "\n\n".join(f"```mermaid\n{f.strip()}\n```" for f in fences)


_INSERT_AFTER_TEXT = re.compile(
    r"Insert after:\s*\n(#{1,6}\s[^\n]+)\s*\n+(?:Return:\s*\n+)?(.*?)(?=Insert after:|Topic:|<!--\s*after:|$)",
    re.DOTALL | re.IGNORECASE,
)


def clean_mermaid_llm_output(raw: str) -> str:
    """
    Keep only valid pipeline markers + mermaid blocks.
    Drops Topic/Context/Insert after/Return scaffolding and accidental lesson prose.
    """
    if not raw or not raw.strip():
        return ""

    parts: list[str] = []

    for match in _REPLACE_MARKER.finditer(raw):
        idx = match.group(1)
        body = _extract_mermaid_only(match.group(2))
        if body:
            parts.append(f"<!-- replace: {idx} -->\n\n{body}")

    for match in _AFTER_MARKER.finditer(raw):
        heading = match.group(1).strip()
        body = _extract_mermaid_only(match.group(2))
        if body:
            parts.append(f"<!-- after: {heading} -->\n\n{body}")

    for match in _INSERT_AFTER_TEXT.finditer(raw):
        heading = match.group(1).strip()
        body = _extract_mermaid_only(match.group(2))
        if body:
            parts.append(f"<!-- after: {heading} -->\n\n{body}")

    if parts:
        return "\n\n".join(parts).strip() + "\n"

    # Fallback: bare mermaid fences without markers (append at end upstream)
    fences = _MERMAID_FENCE.findall(raw)
    if fences:
        return "\n\n".join(f"```mermaid\n{f.strip()}\n```" for f in fences) + "\n"

    # Last resort: strip wrapper lines only
    cleaned = _WRAPPER_ONLY_LINE.sub("", raw)
    return cleaned.strip()


"""Parse and manage <!-- diagram: ## Heading --> placeholders in student notes."""

from __future__ import annotations

import re
from dataclasses import dataclass

from prompts.mermaid_prompts import _extract_h2_headings, _section_context

PLACEHOLDER_RE = re.compile(r"<!--\s*diagram:\s*(.+?)\s*-->", re.IGNORECASE)
DIAGRAM_JSON_RE = re.compile(r"```diagram-json\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
SVG_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(\./diagrams/[^)]+\.svg\)")
MERMAID_BLOCK_RE = re.compile(r"```mermaid\s*\n.*?\n```", re.DOTALL | re.IGNORECASE)


@dataclass(frozen=True)
class DiagramPlaceholder:
    anchor: str
    start: int
    end: int


def normalize_anchor(anchor: str) -> str:
    text = (anchor or "").strip()
    if not text.startswith("##"):
        text = f"## {text.lstrip('#').strip()}"
    return text


def _heading_before_position(markdown: str, pos: int) -> str | None:
    """Return the nearest ## H2 heading text before *pos*."""
    heading: str | None = None
    for line in (markdown[:pos] or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("## ") and not stripped.startswith("###"):
            heading = stripped[3:].strip()
    return heading


def convert_mermaid_blocks_to_placeholders(markdown: str) -> str:
    """
    Replace ```mermaid blocks with <!-- diagram: ## Section --> placeholders.
    Uses the nearest preceding H2 as the anchor so diagram_generator keeps section context.
    """
    text = markdown or ""
    matches = list(MERMAID_BLOCK_RE.finditer(text))
    if not matches:
        return text

    updated = text
    for match in reversed(matches):
        heading = _heading_before_position(text, match.start())
        anchor = normalize_anchor(f"## {heading}" if heading else "## Overview")
        window_start = max(0, match.start() - 250)
        window_end = min(len(text), match.end() + 250)
        window = text[window_start:window_end]
        if PLACEHOLDER_RE.search(window):
            replacement = ""
        else:
            replacement = f"\n<!-- diagram: {anchor} -->\n"
        updated = updated[: match.start()] + replacement + updated[match.end() :]

    updated = MERMAID_BLOCK_RE.sub("", updated)
    updated = re.sub(r"\n{4,}", "\n\n\n", updated)
    return updated.strip() + "\n"


def find_placeholders(markdown: str) -> list[DiagramPlaceholder]:
    items: list[DiagramPlaceholder] = []
    for match in PLACEHOLDER_RE.finditer(markdown or ""):
        items.append(
            DiagramPlaceholder(
                anchor=normalize_anchor(match.group(1)),
                start=match.start(),
                end=match.end(),
            )
        )
    return items


def count_diagram_embeds(markdown: str) -> int:
    return len(DIAGRAM_JSON_RE.findall(markdown or ""))


def has_unfilled_placeholders(markdown: str) -> bool:
    """True when a placeholder is not followed by diagram-json within ~600 chars."""
    text = markdown or ""
    for ph in find_placeholders(text):
        tail = text[ph.end : ph.end + 600]
        if not DIAGRAM_JSON_RE.search(tail):
            return True
    return False


def inject_placeholder_after_heading(markdown: str, heading: str) -> str:
    """Insert placeholder after first paragraph under ## heading if missing."""
    anchor = normalize_anchor(heading)
    if any(p.anchor.lower() == anchor.lower() for p in find_placeholders(markdown)):
        return markdown

    lines = (markdown or "").splitlines()
    target = heading.strip().lower().lstrip("#").strip()
    insert_at: int | None = None
    for i, line in enumerate(lines):
        if line.strip().startswith("## ") and not line.strip().startswith("###"):
            h = line.strip()[3:].strip().lower()
            if h == target or target in h or h in target:
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                while j < len(lines):
                    t = lines[j].strip()
                    if (
                        t.startswith("#")
                        or t.startswith("```")
                        or t.startswith("<!-- diagram:")
                        or t.startswith("- ")
                        or t.startswith("* ")
                    ):
                        break
                    j += 1
                insert_at = j
                break

    placeholder = f"\n<!-- diagram: {anchor} -->\n"
    if insert_at is None:
        return (markdown or "").rstrip() + placeholder

    new_lines = lines[:insert_at] + [placeholder.strip()] + lines[insert_at:]
    return "\n".join(new_lines)


def ensure_min_placeholders(markdown: str, min_count: int) -> str:
    notes = markdown or ""
    existing = find_placeholders(notes)
    if len(existing) >= min_count:
        return notes

    headings = _extract_h2_headings(notes)
    if not headings:
        headings = ["Overview"]

    needed = min_count - len(existing)
    for heading in headings:
        if needed <= 0:
            break
        before = notes
        notes = inject_placeholder_after_heading(notes, heading)
        if notes != before:
            needed -= 1

    while needed > 0:
        notes = (notes.rstrip() + "\n\n<!-- diagram: ## Overview -->\n").strip() + "\n"
        needed -= 1

    return notes


def section_context_for_anchor(markdown: str, anchor: str, max_chars: int = 500) -> str:
    heading = anchor.strip()
    if heading.startswith("## "):
        heading = heading[3:].strip()
    ctx = _section_context(markdown, heading, max_chars=max_chars)
    return ctx or heading


def build_embed_block(spec: dict, svg_rel_path: str) -> str:
    import json

    title = spec.get("title") or "Diagram"
    payload = json.dumps(spec, indent=2, ensure_ascii=False)
    return (
        f"```diagram-json\n{payload}\n```\n\n"
        f"![{title}]({svg_rel_path})\n"
    )


def replace_placeholder(markdown: str, placeholder: DiagramPlaceholder, embed: str) -> str:
    before = markdown[: placeholder.start]
    after = markdown[placeholder.end :]
    # Drop stale embed immediately after placeholder if re-rendering
    after = re.sub(r"^\s*```diagram-json\s*\n.*?\n```\s*", "", after, count=1, flags=re.DOTALL)
    after = re.sub(r"^\s*!\[[^\]]*\]\(\./diagrams/[^)]+\.svg\)\s*", "", after, count=1)
    return before + embed.strip() + "\n\n" + after.lstrip()

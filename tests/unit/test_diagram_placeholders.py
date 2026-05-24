"""Tests for diagram placeholder parsing and embed blocks."""

from utils.diagram_placeholders import (
    build_embed_block,
    convert_mermaid_blocks_to_placeholders,
    ensure_min_placeholders,
    find_placeholders,
    inject_placeholder_after_heading,
)

SAMPLE = """# Topic

## Introduction

Some intro text.

## Core Concepts

More content here.
"""


class TestDiagramPlaceholders:
    def test_find_placeholders(self):
        md = SAMPLE + "\n<!-- diagram: ## Introduction -->\n"
        found = find_placeholders(md)
        assert len(found) == 1
        assert "Introduction" in found[0].anchor

    def test_inject_after_heading(self):
        out = inject_placeholder_after_heading(SAMPLE, "Introduction")
        assert "<!-- diagram:" in out
        assert find_placeholders(out)

    def test_ensure_min_placeholders(self):
        out = ensure_min_placeholders(SAMPLE, min_count=2)
        assert len(find_placeholders(out)) >= 2

    def test_build_embed_block(self):
        spec = {"title": "Flow", "layout": "LR", "nodes": [], "edges": []}
        block = build_embed_block(spec, "./diagrams/fig-01.svg")
        assert "```diagram-json" in block
        assert "![Flow](./diagrams/fig-01.svg)" in block

    def test_convert_mermaid_to_placeholder(self):
        md = """## AI Basics

Intro text.

```mermaid
graph TD
A --> B
```
"""
        out = convert_mermaid_blocks_to_placeholders(md)
        assert "```mermaid" not in out
        assert "<!-- diagram: ## AI Basics -->" in out

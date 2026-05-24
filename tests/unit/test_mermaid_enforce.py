"""Tests for Mermaid diagram enforcement and merge."""

from utils.helpers import replace_mermaid_block_by_index
from utils.mermaid_enforce import (
    apply_mermaid_repair_patch,
    count_mermaid_diagrams,
    ensure_mermaid_diagrams,
    merge_mermaid_supplements,
)

SAMPLE_NOTES = """# Python OOP

## Introduction to OOP

Some text about OOP.

## Classes

More text.
"""

SUPPLEMENT = """<!-- after: ## Introduction to OOP -->
```mermaid
graph TD
    A["OOP"] --> B["Classes"]
    style A fill:#1a1a2e,stroke:#7c3aed,color:#e2e8f0
    style B fill:#16213e,stroke:#2563eb,color:#e2e8f0
```
"""


class TestMermaidMerge:
    def test_count_zero(self):
        assert count_mermaid_diagrams(SAMPLE_NOTES) == 0

    def test_merge_by_marker(self):
        merged = merge_mermaid_supplements(SAMPLE_NOTES, SUPPLEMENT)
        assert count_mermaid_diagrams(merged) == 1
        assert "Some text about OOP" in merged
        idx_text = merged.index("Some text about OOP")
        idx_mermaid = merged.index("graph TD")
        assert idx_mermaid > idx_text

    def test_merge_fallback_append(self):
        orphan = "```mermaid\ngraph TD\nA-->B\nstyle A fill:#1a1a2e,stroke:#7c3aed,color:#e2e8f0\n```"
        merged = merge_mermaid_supplements(SAMPLE_NOTES, orphan)
        assert count_mermaid_diagrams(merged) == 1


class TestEnsureMermaid:
    def test_skips_when_enough(self):
        notes_with_four = SAMPLE_NOTES + (
            "\n```mermaid\ngraph TD\nA-->B\nstyle A fill:#1a1a2e,stroke:#7c3aed,color:#e2e8f0\n```\n"
        ) * 4

        class FakeLLM:
            def complete(self, **kwargs):
                raise AssertionError("should not call LLM")

        result = ensure_mermaid_diagrams(
            notes_with_four, {"topic": "OOP"}, FakeLLM(), errors=[]
        )
        assert count_mermaid_diagrams(result) == 4
        assert "flowchart TD" in result

    def test_calls_supplement_when_missing(self, monkeypatch):
        monkeypatch.setenv("MIN_MERMAID_DIAGRAMS", "2")
        monkeypatch.setenv("MERMAID_GENERATION_MODE", "mermaid")

        class FakeLLM:
            def complete(self, **kwargs):
                return SUPPLEMENT + "\n<!-- after: ## Classes -->\n```mermaid\ngraph LR\nX-->Y\nstyle X fill:#1a1a2e,stroke:#7c3aed,color:#e2e8f0\nstyle Y fill:#16213e,stroke:#2563eb,color:#e2e8f0\n```"

        errors: list = []
        result = ensure_mermaid_diagrams(
            SAMPLE_NOTES, {"topic": "OOP"}, FakeLLM(), errors=errors
        )
        assert count_mermaid_diagrams(result) >= 2

    def test_retries_repair_when_validation_fails(self, monkeypatch):
        monkeypatch.setenv("MIN_MERMAID_DIAGRAMS", "1")
        monkeypatch.setenv("MERMAID_MAX_RETRIES", "2")
        monkeypatch.setenv("MERMAID_GENERATION_MODE", "mermaid")
        calls = {"n": 0}
        bad = "<!-- after: ## Introduction to OOP -->\n```mermaid\ngraph TD\nT3[Bad: label]\n```"
        good = SUPPLEMENT

        class FakeLLM:
            def complete(self, **kwargs):
                calls["n"] += 1
                return bad if calls["n"] == 1 else good

        result = ensure_mermaid_diagrams(
            SAMPLE_NOTES, {"topic": "OOP"}, FakeLLM(), errors=[]
        )
        assert calls["n"] >= 2
        assert 'T3["Bad: label"]' in result or count_mermaid_diagrams(result) >= 1


class TestMermaidBlockReplace:
    def test_replace_by_index(self):
        notes = SAMPLE_NOTES + "\n```mermaid\ngraph TD\nA-->B\n```\n"
        updated = replace_mermaid_block_by_index(
            notes,
            1,
            "graph TD\nA[\"Fixed\"] --> B\nstyle A fill:#1a1a2e,stroke:#7c3aed,color:#e2e8f0",
        )
        assert 'A["Fixed"]' in updated
        assert count_mermaid_diagrams(updated) == 1

    def test_apply_repair_with_replace_marker(self):
        notes = SAMPLE_NOTES + "\n```mermaid\ngraph TD\nBad[Label: x]\n```\n"
        patch = (
            "<!-- replace: 1 -->\n"
            "```mermaid\ngraph TD\nA[\"Label: x\"] --> B\n"
            "style A fill:#1a1a2e,stroke:#7c3aed,color:#e2e8f0\n"
            "style B fill:#16213e,stroke:#2563eb,color:#e2e8f0\n```"
        )
        updated = apply_mermaid_repair_patch(notes, patch)
        assert 'A["Label: x"]' in updated
        assert "Bad[Label: x]" not in updated

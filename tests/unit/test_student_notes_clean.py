"""Tests for student notes and mermaid patch cleaning."""

from utils.mermaid_patch_clean import clean_mermaid_llm_output
from utils.student_notes_clean import clean_student_notes

LEAKED_SUPPLEMENT = """Topic: OOP Basics

Context:
Some context here about classes.

Insert after:
## 2. Classes

Return:

### Extra prose that should not appear

```mermaid
flowchart TD
A["One"] --> B["Two"]
style A fill:#1a1a2e,stroke:#7c3aed,color:#e2e8f0
style B fill:#1a1a2e,stroke:#7c3aed,color:#e2e8f0
```
"""

STUDENT_WITH_LEAKS = """# Lesson

Topic: OOP

Insert after:
## Section

Return:

## Section

Body text.

> **👨‍🏫 TEACHING NOTE:** Tell students about OOP.
"""


def test_clean_mermaid_llm_output_keeps_marker_and_diagram_only():
    out = clean_mermaid_llm_output(LEAKED_SUPPLEMENT)
    assert "<!-- after:" in out
    assert "```mermaid" in out
    assert "Topic:" not in out
    assert "Return:" not in out
    assert "Extra prose" not in out


def test_clean_student_notes_strips_wrapper_and_tutor_lines():
    out = clean_student_notes(STUDENT_WITH_LEAKS)
    assert "Topic:" not in out
    assert "Insert after:" not in out
    assert "TEACHING NOTE" not in out
    assert "Body text." in out

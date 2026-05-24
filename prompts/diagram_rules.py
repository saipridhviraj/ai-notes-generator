"""Student-notes diagram placeholder rules (JSON + SVG pipeline — no Mermaid)."""


def get_diagram_placeholder_rules(min_diagrams: int = 4) -> str:
    return f"""DIAGRAM PLACEHOLDER RULES (CRITICAL — violations break the pipeline):

- Minimum {min_diagrams} diagrams per file
- NEVER write ```mermaid``` blocks — they are forbidden in student notes
- After each major concept section, insert ONE placeholder on its own line:
  <!-- diagram: ## Exact H2 Heading -->
  Use the exact ## heading text from that section (include emoji if present)
- Do NOT write JSON, SVG, React, or graph TD/LR syntax in the notes
- Place each placeholder immediately after the first paragraph under that ## section
- If research lists ## Suggested Diagrams, add a placeholder in each matching section
- The pipeline generates diagrams automatically from these placeholders

Example (inside your markdown):
## 🔍 How RAG Works

Retrieval-augmented generation combines search with an LLM.

<!-- diagram: ## 🔍 How RAG Works -->"""

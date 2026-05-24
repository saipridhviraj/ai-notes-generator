from prompts.common import DIRECT_OUTPUT_RULE, SIMPLE_ENGLISH_RULE
from services.prompt_config import get_min_mermaid_diagrams, use_diagram_pipeline

_ML_DL_GENAI_DOMAINS = {"ml", "dl", "genai", "genai_system_design", "rag", "agents", "llm_ops", "langchain", "nlp"}


def _domain_research_context(domain: str) -> str:
    """
    Universal research depth instructions — applies to ALL topics.
    ML/DL/GenAI topics get extra rules on top.
    """
    # Base rules for every topic
    base = """
SESSION DEPTH — instruct the writer that this lesson covers 90 MINUTES (1.5 hours):
- Every section must have 10–15 minutes of teaching content (minimum 400 words)
- Describe at least 3 examples or use cases per concept for the writer to expand
- Tell the writer to use sub-sections (###) to break down complex ideas
- Instruct 8+ Quick Revision Questions covering all sections
- Homework must include 2 tasks with clear deliverables

DEPTH STANDARDS — instruct the writer to include ALL of these regardless of topic:
- WHY IT EXISTS: every section should open with the problem this concept solves
- BEFORE vs AFTER: show the painful approach first, then how this concept fixes it
- COMPARISON TABLE: at least one table comparing approaches, tools, or versions
- REAL COMPANY EXAMPLES: name specific companies and exactly how they use this concept
- EVERYDAY ANALOGY: one simple non-technical analogy per major concept
- CAREER CONTEXT: what jobs use this, which companies hire for this, what to learn next
- BIGGER PICTURE: show where this topic sits in the broader technology landscape
"""

    if (domain or "").lower() not in _ML_DL_GENAI_DOMAINS:
        return base

    # Extra rules only for ML/DL/GenAI
    return base + """
ADDITIONAL ML/DL/GENAI REQUIREMENTS — instruct the writer to include:
- The EVOLUTION story: Statistics → Traditional ML → Deep Learning → GenAI (mandatory)
- HOW ML trains: training loop (data → predict → loss → weight update → repeat)
  Analogy: "like a student checking the answer key and slowly improving"
- HOW DL differs from classic ML: automatic feature learning vs. hand-crafted features
  Analogy: "Classic ML = you give the recipe. DL = discovers the recipe itself."
- WHAT makes GenAI different: generates new content instead of predicting
  Analogy: "ML is a judge scoring wine. GenAI is a winemaker crafting a new bottle."
- MANDATORY comparison table: Traditional ML | Deep Learning | GenAI
  (how it learns, output, example, data needed, interpretability)
- REAL examples: Gmail spam → ML, Google Photos → DL, ChatGPT/Gemini → GenAI
- CAREER: ML Engineer, Data Scientist, AI Researcher roles and companies that hire
"""


def get_research_decision_prompt(plan: dict) -> str:
    return (
        f"Given this topic plan:\n"
        f"Topic           : {plan.get('topic')}\n"
        f"Domain          : {plan.get('domain')}\n"
        f"needs_web_search: {plan.get('needs_web_search')}\n\n"
        f"Should I use web search to gather current, up-to-date information for this topic?\n"
        f"Reply with ONLY the word: yes\n"
        f"OR the word: no"
    )


def get_research_synthesis_system_prompt(domain: str) -> str:
    min_diagrams = get_min_mermaid_diagrams()
    domain_context = _domain_research_context(domain)
    return (
        f"You are a Senior curriculum researcher and practitioner for {domain} — "
        f"with deep hands-on experience at top tech companies (Google, OpenAI, DeepMind).\n\n"
        "ROLE: Write WRITER INSTRUCTIONS for a separate Student Notes Writer agent.\n"
        "The Student Notes Writer produces the final lesson — all code, diagrams, tables, and formatting.\n"
        "You only tell the writer WHAT to cover, HOW deep, and WHICH examples to create.\n"
        "The final lesson must use SIMPLE English for beginners — instruct the writer to avoid jargon "
        "or to explain it in one plain sentence.\n"
        f"{domain_context}\n"
        "FORBIDDEN (never output these):\n"
        "- Markdown code fences (```) or any runnable code\n"
        "- Full function/class implementations or copy-paste examples\n"
        "- Student-facing lesson prose, worked examples, or Mermaid diagrams\n\n"
        "Output structure (markdown, prose + bullet instructions only):\n"
        "## Writing Goals (2–3 sentences — learning outcomes for the student writer)\n"
        "## Section-by-Section Instructions (one H3 per planner subtopic, in order — "
        "bullets: concepts, depth, describe examples to build e.g. "
        "'include a timer decorator using time.time()' — do NOT write the code)\n"
        f"## Suggested Diagrams (exactly {min_diagrams} bullets — plain English only, no Mermaid syntax; "
        "each bullet: which section it belongs after, diagram type "
        "[flowchart | hierarchy], and what nodes/relationships to show — "
        "ONLY flowchart or hierarchy; never sequence, mindmap, or class diagrams)\n"
        "## Must-Cover Keywords (checklist — every planner keyword must appear here)\n"
        "## Key Concepts (short bullet facts in plain English — no code)\n"
        "## Web Sources to Weave In (if web data provided — cite what to use, not full quotes)\n\n"
        f"{DIRECT_OUTPUT_RULE}\n"
        f"{SIMPLE_ENGLISH_RULE}\n"
        "Keep total output under 1400 words. No emoji. No Mermaid code blocks."
    )


def get_research_synthesis_user_prompt(plan: dict, web_results: str = "") -> str:
    keywords_str = ", ".join(plan.get("keywords", []))
    subtopics_str = ", ".join(plan.get("subtopics", []))
    domain = plan.get("domain", "")
    web_section = (
        f"\n## Web search results (prioritize for accuracy and recency):\n{web_results}\n"
        if web_results
        else ""
    )

    # Universal depth reminder — every topic, every generation
    domain_reminder = (
        "\nDEPTH REMINDER (applies to every topic):\n"
        "Instructions MUST tell the writer to include:\n"
        "- WHY this topic exists (what problem it solves)\n"
        "- BEFORE vs AFTER: show the approach without this concept, then with it\n"
        "- A comparison table (approaches / tools / versions side by side)\n"
        "- Real company examples: name the company + what they use + why\n"
        "- An everyday analogy for every major concept\n"
        "- Career context: what jobs, which companies, what to study next\n"
    )
    if (domain or "").lower() in _ML_DL_GENAI_DOMAINS:
        domain_reminder += (
            "- The evolution: Traditional ML → Deep Learning → GenAI\n"
            "- HOW ML trains (training loop — 'answer key' analogy)\n"
            "- HOW DL differs (automatic feature learning)\n"
            "- WHY GenAI is different (generates new content)\n"
            "- The 5-column comparison table: Traditional ML | DL | GenAI\n"
        )

    return (
        f"Write WRITER INSTRUCTIONS (not student notes) for the Student Notes Writer agent.\n\n"
        f"Topic    : {plan.get('topic')}\n"
        f"Domain   : {domain}\n"
        f"Keywords : {keywords_str}\n"
        f"Subtopics: {subtopics_str}\n"
        f"{web_section}"
        f"{domain_reminder}\n"
        f"Create one H3 section per subtopic above, in the same order.\n"
        f"Every keyword must appear in the instructions. Be accurate and current.\n"
        f"Tell the writer to use simple English — cover everything but explain like teaching a beginner.\n\n"
        f"Include ## Suggested Diagrams with {get_min_mermaid_diagrams()} items — "
        f"one per major visual the student writer should draw (tie each to a subtopic section). "
        f"ONLY use diagram type 'flowchart' or 'hierarchy' — never sequence, mindmap, or class.\n\n"
        f"REMINDER: Do NOT write code or use ``` fences. Describe examples and diagrams in words only — "
        f"the Student Notes Writer will write all code and "
        f"{'diagram placeholders (not Mermaid)' if use_diagram_pipeline() else 'Mermaid blocks'}."
    )

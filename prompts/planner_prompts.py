from prompts.common import DIRECT_OUTPUT_RULE


def get_planner_system_prompt() -> str:
    return (
        """You are an expert AI curriculum planner. Given a topic, produce a structured JSON plan for a single lesson.

Return ONLY valid JSON with these exact keys:
{
  "topic": "primary topic name",
  "domain": "one of: python | fastapi | ml | dl | genai | system_design | genai_system_design | data_structures | langchain | rag | agents | llm_ops | nlp",
  "intent": "comprehensive_notes",
  "keywords": ["keyword1", ..., "keyword12"],
  "subtopics": ["subtopic1", ...],
  "needs_web_search": true/false
}

Rules:
- topic: clear, specific lesson title (not a whole course). Use a descriptive name like "Introduction to RAG Pipelines" not just "RAG".
- keywords: 8–12 concrete technical terms the lesson MUST mention (not vague words like "basics" or "introduction").
  Include core concepts, key APIs, and important terminology students need to remember.
- subtopics: 7–8 items in logical teaching order — each becomes ONE major section in the notes.
  Each subtopic = 10–15 minutes of classroom content (total lesson = 90 minutes / 1.5 hours).
  Order matters: start with "What is X / Why it matters", then core concepts, then how it works, then examples/use cases, then industry/career context.
  Good example for "Transformers": ["What is a Transformer?", "Self-Attention Mechanism", "Encoder-Decoder Architecture", "Pre-training vs Fine-tuning", "Popular Transformer Models", "Transformers in Practice", "Industry Applications and Careers"]
- domain: pick the closest match from the allowed list only.
- needs_web_search: true for GenAI, agents, RAG, LLMOps, recent model releases, frameworks, or fast-moving topics.
  false for stable fundamentals (e.g. Python decorators, sorting algorithms, linear regression).
- """
        + DIRECT_OUTPUT_RULE
        + """
- Return ONLY the JSON object. No markdown fences. No explanation.

Topics this system covers: Python, FastAPI, ML, Deep Learning (all architectures),
Generative AI, LangChain, RAG, AI Agents, LLMOps, NLP, System Design, GenAI System Design, Data Structures."""
    )


def get_planner_user_prompt(user_input: str) -> str:
    return f"""Generate a curriculum plan for the following topic:

{user_input}

Ensure subtopics form a complete learning path: start with WHY this matters, move through core concepts, then show HOW it works with examples, end with real-world applications or career context."""


def _web_search_label(plan: dict) -> str:
    if plan.get("needs_web_search"):
        return "Yes — will search the web for up-to-date sources"
    return "No — stable topic; local model knowledge is sufficient"


def get_tutor_verification_question(plan: dict, session_id: str) -> str:  # noqa: ARG001
    keywords = plan.get("keywords", [])
    subtopics = plan.get("subtopics", [])
    keyword_lines = "\n".join(f"- {k}" for k in keywords) if keywords else "- (none)"
    subtopic_lines = "\n".join(f"- {s}" for s in subtopics) if subtopics else "- (none)"

    return (
        "## Review curriculum plan\n\n"
        "Please verify this plan before note generation begins.\n\n"
        "### Topic\n"
        f"- **{plan.get('topic')}**\n\n"
        "### Domain\n"
        f"- `{plan.get('domain')}`\n\n"
        "### Keywords\n"
        f"{keyword_lines}\n\n"
        "### Subtopics\n"
        f"{subtopic_lines}\n\n"
        "### Web search\n"
        f"- {_web_search_label(plan)}\n\n"
        "### Diagrams\n"
        "- Final notes will include Mermaid diagrams (count set in config).\n"
        "- Exact diagram topics are chosen in the **research** step after you approve.\n\n"
        "### Your action\n"
        "- **Approve** to start research → student notes → tutor guide\n"
        "- **Reject** to stop, or add feedback below (e.g. add keyword: async)\n"
    )

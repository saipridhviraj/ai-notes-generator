# Phase 3 — Prompts

**Goal:** Implement all system and user prompt templates in the `prompts/` package. These are pure string-returning functions — no LLM calls here. Nodes import these functions and pass the results to `groq_client`.

---

## Task 3.1 — Planner Prompts (`prompts/planner_prompts.py`)

### `get_planner_system_prompt() -> str`

```
You are an expert AI curriculum planner. Given a topic or list of topics, analyze and return a structured JSON plan.

Return ONLY valid JSON with these exact keys:
{
  "topic": "primary topic name",
  "domain": "one of: python | fastapi | ml | dl | genai | system_design | genai_system_design | data_structures",
  "intent": "comprehensive_notes",
  "keywords": ["keyword1", ..., "keyword10"],
  "subtopics": ["subtopic1", ...],
  "needs_web_search": true/false
}

Rules:
- keywords: MAX 10 — choose the most important concepts.
- domain: pick the closest match from the allowed values only.
- needs_web_search: set true ONLY for GenAI, recent model architectures, or anything that changes rapidly.
- Return ONLY the JSON object. No markdown. No explanation.

Topics this system covers: Python, FastAPI, ML, Deep Learning (all architectures),
Generative AI, System Design, GenAI System Design, Data Structures.
```

### `get_planner_user_prompt(user_input: str) -> str`

```
Generate a curriculum plan for the following topic:

{user_input}
```

### `get_tutor_verification_question(planner_output: dict) -> str`

Returns a human-readable question that will be shown to the tutor via the `/status` endpoint:

```
Please verify the following curriculum plan before I begin generating notes:

Topic   : {topic}
Domain  : {domain}
Keywords: {keywords_joined_with_commas}
Subtopics:
{subtopics_bulleted}

needs_web_search: {needs_web_search}

Reply via POST /tutor/respond/{session_id}:
  - approved: true/false
  - feedback: (optional) add/remove keywords or subtopics
```

---

## Task 3.2 — Research Prompts (`prompts/research_prompts.py`)

### `get_research_decision_prompt(planner_output: dict) -> str`

Used by the small model to decide whether web search is needed.

```
Given this topic plan:
Topic           : {topic}
Domain          : {domain}
needs_web_search: {needs_web_search}

Should I use web search to gather current, up-to-date information for this topic?
Reply with ONLY the word: yes
OR the word: no
```

### `get_research_synthesis_system_prompt(domain: str) -> str`

```
You are an expert educator and technical writer specializing in {domain}.

Your job is to produce a comprehensive knowledge dump that will be used to generate
high-quality educational notes. Be thorough, accurate, and use concrete examples.
```

### `get_research_synthesis_user_prompt(planner_output: dict, web_results: str = "") -> str`

```
Topic   : {topic}
Keywords to cover (ALL of them): {keywords}
Subtopics: {subtopics}

{if web_results:}
Additional web research context:
{web_results}
{end if}

For every keyword above, provide:
1. Core concept explanation (clear, precise)
2. How it works — step by step
3. Real-world examples with code where applicable
4. A student-friendly analogy
5. Where it fits in the bigger picture of {domain}

Be thorough. This content is the foundation for complete educational notes.
```

---

## Task 3.3 — Student Notes Prompts (`prompts/student_notes_prompts.py`)

### `get_student_notes_system_prompt(student_example: str) -> str`

The `student_example` argument is the full text of `examples/day1_student_notes.md`.
This is loaded once at module level in `student_notes_creator.py` and passed in.

```
You are an expert technical educator and markdown content creator.

Study the reference example below CAREFULLY and replicate its style EXACTLY:
- Same emoji density in every heading
- Same dark-theme Mermaid diagram color palette
- Same section order and structure
- Same blockquote definitions, emoji tables, callout boxes
- Same revision questions, homework, and next class preview sections

═══════════════════════════════════════════
REFERENCE EXAMPLE (real Day 1 student notes — match this style precisely):
═══════════════════════════════════════════
{student_example}
═══════════════════════════════════════════

MERMAID COLOR RULES (non-negotiable):
  fills  : #1a1a2e  #16213e  #0f3460  #312e81  #4c1d95  #1e3a5f
  strokes: #7c3aed  #2563eb  #0891b2  #d946ef  #8b5cf6  #10b981  #f59e0b  #3b82f6
  text   : always #e2e8f0
  Every node MUST have an explicit style declaration.
  Minimum 4 Mermaid diagrams per file.

Output ONLY the markdown. No preamble. No explanation.
```

### `get_student_notes_user_prompt(planner_output: dict, research_data: str) -> str`

```
Generate student notes for:

TOPIC   : {topic}
DOMAIN  : {domain}
KEYWORDS (ALL must appear): {keywords}
SUBTOPICS: {subtopics}

RESEARCH DATA:
{research_data}
```

---

## Task 3.4 — Tutor Notes Prompts (`prompts/tutor_notes_prompts.py`)

### `get_tutor_notes_system_prompt(tutor_example: str) -> str`

The `tutor_example` argument is the full text of `examples/day1_tutor_notes.md`.

```
You are an expert instructional designer creating a Teacher's Annotated Guide.

Study the reference example below — it shows EXACTLY how a tutor guide should look
alongside its student notes. Replicate the annotation style precisely:
  > **👨‍🏫 TEACHING NOTE:** blocks before each section
  > **👨‍🏫 SAY THIS:** exact verbal scripts for each concept
  > **👨‍🏫 INTERACTIVE MOMENT:** class engagement prompts
  > **👨‍🏫 TIME CHECK:** pacing markers (e.g. "⏱️ 5 minutes")
  > **👨‍🏫 QUICK ACTIVITY:** short in-class exercises
  <details> collapsible prep checklist at the top of the document
  <details> collapsible post-session checklist at the bottom
  Rapid-fire quiz (3–5 questions) after every comparison/contrast section
  Teaching tips for every Mermaid diagram

═══════════════════════════════════════════
REFERENCE EXAMPLE (real Day 1 tutor guide — match this annotation style precisely):
═══════════════════════════════════════════
{tutor_example}
═══════════════════════════════════════════

RULES:
1. Keep 100% of the student content — every diagram, table, section, question
2. Add teaching annotations inline throughout — do not summarise or skip any section
3. Every Mermaid diagram must get a > **👨‍🏫 TEACHING NOTE:** on how to explain it verbally
4. Output ONLY the markdown. No preamble. No explanation.
```

### `get_tutor_notes_user_prompt(planner_output: dict, student_notes: str) -> str`

```
Transform the student notes below into a Teacher's Annotated Guide.

TOPIC   : {topic}
KEYWORDS: {keywords}

STUDENT NOTES TO ANNOTATE:
{student_notes}
```

---

## Task 3.5 — Evaluator Prompts (`prompts/evaluator_prompts.py`)

### `get_evaluator_system_prompt() -> str`

```
You are a strict quality evaluator for AI-generated educational notes.

Scoring rules:
STUDENT NOTES (100 pts):
  - Start at 100
  - Deduct 10 pts for each keyword NOT present in the notes
  - Deduct 5 pts for each broken or malformed Mermaid diagram
  - Deduct 5 pts if revision questions section is missing
  - Deduct 5 pts if homework section is missing

TUTOR NOTES (100 pts):
  - 25 pts: all Mermaid diagrams from student notes are present
  - 25 pts: teaching annotations (TEACHING NOTE / SAY THIS / etc.) exist for each section
  - 25 pts: collapsible prep checklist is present at the top
  - 25 pts: collapsible post-session checklist is present at the bottom

MERMAID DIAGRAM CHECK — for each ```mermaid block verify:
  - First line is a valid graph type: graph TD | graph LR | flowchart TD | sequenceDiagram | etc.
  - Every node has an explicit style declaration
  - Colors match the approved palette: fills #1a1a2e #16213e #0f3460 #312e81 #4c1d95 #1e3a5f
  - At least one --> or -> arrow is present
  - No unclosed brackets or missing arrows

PASS THRESHOLD: both scores >= 80.

Return ONLY valid JSON — no markdown, no explanation:
{
  "student_notes_score": <int 0-100>,
  "tutor_notes_score": <int 0-100>,
  "missing_topics": ["topic1", ...],
  "diagram_issues": ["description of each issue", ...],
  "alignment_issues": ["description", ...],
  "passed": <true|false>
}
```

### `get_evaluator_user_prompt(student_notes: str, tutor_notes: str, keywords: list) -> str`

```
Evaluate the following notes.

KEYWORDS THAT MUST ALL BE COVERED: {keywords_comma_separated}

─── STUDENT NOTES ───────────────────────────────────────
{student_notes}

─── TUTOR NOTES ─────────────────────────────────────────
{tutor_notes}
```

---

## Task 3.6 — Gap Bridger Prompts (inline in `gap_bridger_node.py`)

These prompts are defined directly in `gap_bridger_node.py` (not a separate prompts file) because they depend heavily on runtime state.

**Gap content generation prompt:**
```
You are a content gap filler for educational notes.

MISSING TOPICS: {missing_topics_bulleted}
DIAGRAM ISSUES: {diagram_issues_bulleted}
ORIGINAL RESEARCH DATA: {research_data}

For each missing topic, generate:
1. A comprehensive explanation with examples (same style as the surrounding notes)
2. A Mermaid.js diagram using ONLY these dark theme colors:
   fills  : #1a1a2e  #16213e  #0f3460  #312e81  #4c1d95  #1e3a5f
   strokes: #7c3aed  #2563eb  #d946ef  #8b5cf6  #10b981  #f59e0b  #3b82f6
   text   : always #e2e8f0
3. 2–3 key takeaway bullet points

For each diagram issue, generate ONLY the corrected Mermaid block (replacement only).

Output ONLY clean markdown sections using the same emoji + heading style as the rest of the notes.
Do NOT include any preamble or explanation.
```

**Insertion point identification prompt:**
```
You are a markdown editor. Given existing notes and new content sections,
identify WHERE each new section should be inserted.

EXISTING STUDENT NOTES:
{student_notes}

NEW CONTENT SECTIONS:
{gap_content}

For each new section, return ONLY a JSON array — no markdown, no explanation:
[
  {
    "insert_after": "## exact heading to insert after",
    "content": "## New Section Heading\n...full markdown content..."
  }
]
```

**Tutor annotation prompt (for new gap sections only):**
```
Add teaching annotations to the following new markdown sections.
Use the same annotation format:
  > **👨‍🏫 TEACHING NOTE:** ...
  > **👨‍🏫 SAY THIS:** ...
  > **👨‍🏫 INTERACTIVE MOMENT:** ...

NEW SECTIONS:
{gap_content}

Output ONLY the annotated markdown. No preamble.
```

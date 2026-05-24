# Phase 2 — Services Layer

**Goal:** Implement the three service wrappers that all nodes depend on — Groq LLM client, Tavily search client, and file service. These are stateless utility classes instantiated once and injected into nodes.

---

## Task 2.1 — Groq Client (`services/groq_client.py`)

A thin wrapper around the Groq SDK that provides model routing by complexity level.

### Model registry (hardcoded, never change)

```python
MODELS = {
    "small":     "llama-3.1-8b-instant",
    "large":     "llama-3.3-70b-versatile",
    "reasoning": "deepseek-r1-distill-llama-70b",
}
```

### Class: `GroqClient`

**`__init__`**
- Load `GROQ_API_KEY` from environment (via `os.getenv`).
- Instantiate `groq.Groq(api_key=...)`.
- Raise `ValueError` with a clear message if the key is missing.

**`complete(prompt, size, system, temperature, max_tokens) -> str`**

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `prompt` | `str` | required | User message |
| `size` | `str` | `"large"` | One of `"small"`, `"large"`, `"reasoning"` |
| `system` | `str` | `""` | System message — omit from messages list if empty |
| `temperature` | `float` | `0.7` | |
| `max_tokens` | `int` | `8192` | |

- Build `messages` list: prepend `{"role": "system", "content": system}` only when `system` is non-empty.
- Call `self.client.chat.completions.create(model=MODELS[size], messages=messages, temperature=temperature, max_tokens=max_tokens)`.
- Return `response.choices[0].message.content`.
- Wrap in `try/except` — on any exception log to `stderr` and re-raise.

**`complete_json(prompt, size, system, temperature) -> dict`**

- Same as `complete` but sets `max_tokens=1024` and parses the response as JSON.
- Strip any markdown code fences (` ```json ... ``` `) before parsing.
- Raise `ValueError("GroqClient: response was not valid JSON")` if parsing fails.

### Module-level singleton

```python
groq_client = GroqClient()
```

Nodes import this singleton:
```python
from services.groq_client import groq_client
```

**Acceptance criteria:**
- `groq_client.complete("Hello", size="small")` returns a non-empty string.
- `complete_json` strips code fences correctly and returns a dict.
- Missing API key raises `ValueError` immediately on import.

---

## Task 2.2 — Tavily Client (`services/tavily_client.py`)

A wrapper for the Tavily search API, used only by `research_node.py`.

### Class: `TavilyClient`

**`__init__`**
- Load `TAVILY_API_KEY` from environment.
- Instantiate `tavily.TavilyClient(api_key=...)`.
- Raise `ValueError` with a clear message if the key is missing.

**`search(query, max_results=3) -> list[dict]`**

- Call `self.client.search(query=query, max_results=max_results)`.
- Return a list of result dicts. Each dict must have at least `{"title": str, "url": str, "content": str}`.
- If the API call fails, log the error to `stderr` and return `[]` (do not raise — research is optional).

**`search_keywords(keywords, max_results_per_keyword=3) -> str`**

- Accepts a list of keyword strings.
- Calls `self.search(keyword, max_results_per_keyword)` for each keyword.
- **Limit: call at most 3 keywords** to control latency (slice `keywords[:3]`).
- Deduplicate results by URL.
- Format the collected results into a single markdown string:
  ```
  ## Web Research Results

  ### [Title](url)
  Content snippet...

  ---
  ```
- Return the formatted string.

### Module-level singleton

```python
tavily_client = TavilyClient()
```

**Acceptance criteria:**
- `tavily_client.search("LangGraph tutorial", max_results=2)` returns a list with `title`, `url`, `content` keys.
- When `TAVILY_API_KEY` is missing, instantiation raises `ValueError`.
- At most 3 Tavily API calls are made regardless of how many keywords are passed.

---

## Task 2.3 — File Service (`services/file_service.py`)

Handles saving generated Markdown notes to disk and reading example files.

### Functions

**`save_markdown(content: str, filename: str, output_dir: Optional[Path] = None) -> Path`**

- Default `output_dir` = `Path.cwd()`.
- Create `output_dir` if it does not exist (`mkdir(parents=True, exist_ok=True)`).
- Write `content` to `output_dir / filename` with `encoding="utf-8"`.
- Return the absolute `Path` object.
- Wrap in `try/except` — append error message and re-raise.

**`load_example(filename: str) -> str`**

- Build path: `Path(__file__).parent.parent / "examples" / filename`.
- If the file does not exist, raise `FileNotFoundError` with this exact message:
  ```
  Missing required example file: examples/{filename}
  Copy your Day 1 notes into the examples/ folder before running.
  See README.md for setup instructions.
  ```
- Read and return content as UTF-8 string.

**`slugify(text: str) -> str`**

- Convert topic text to a filesystem-safe slug.
- Lowercase, replace spaces and special chars with underscores.
- Strip leading/trailing underscores.
- Example: `"Python Decorators & Context Managers"` → `"python_decorators_context_managers"`

**Acceptance criteria:**
- `save_markdown("# Hello", "test.md")` writes a file to `cwd`.
- `load_example("day1_student_notes.md")` raises `FileNotFoundError` when file is absent.
- `slugify("Python Decorators & Context Managers")` → `"python_decorators_context_managers"`.

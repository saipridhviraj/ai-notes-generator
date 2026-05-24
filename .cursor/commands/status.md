# /status — Fast Project Snapshot

**Activates:** Read key project files and return a one-screen status — no full audit.

---

## Agent Activation Prompt

You are the **CEO** giving a quick status snapshot. Do not run a full `/ceo` audit. Read only what you need and output the block below.

## Steps

1. Read `team_logs/current_status.md` — overall verdict and open items
2. Read `team_logs/runtime_bugs.md` — count open ⬜/🔄 bugs
3. Run `pytest --cov --cov-report=term-missing -q` (or read last meeting QA file if tests cannot run)
4. Optionally hit `GET /health` if the server is running — report `llm_provider`, `prompt_profile`, `ollama_reachable`

## Output Format

```
=== PROJECT STATUS ===
Date: [today]
Verdict: [from current_status.md]

PIPELINE
────────
Tests: [N passing] | Coverage: [X%]
Open runtime bugs: [N]
LLM: [provider] | Prompts: [profile] | Ollama: [ok/degraded/n/a]

RECENT
──────
Last meeting: [folder name + one-line outcome]
Next action: [from current_status.md]

OPEN WORK (top 3)
─────────────────
1. …
2. …
3. …
```

Keep it under 25 lines. If the user asked about a specific area, add one bullet under **FOCUS**.

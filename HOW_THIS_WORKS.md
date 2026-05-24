# How This Project's Team System Works

This project has a virtual engineering team built into `.cursor/rules/`. Every agent is a specialist with Google-level expertise in their domain. You talk to them through commands in the Cursor chat.

---

## The Team

| Agent | Command | Role |
|-------|---------|------|
| CEO | `/ceo` | Runs the full team, produces the verdict |
| Product Owner | `/po` | Validates requirements against specs |
| Project Manager | `/pm` | Tracks tasks, milestones, risks |
| System Architect | `/arch` | Reviews design, produces ADRs |
| Senior Backend Dev | `/backend` | Fixes bugs, implements features |
| QA Engineer | `/qa` | Writes and runs the test suite |
| Security Auditor | `/security` | OWASP + STRIDE scan |
| DevOps / SRE | `/devops` | Docker, CI/CD, deployment |
| Frontend Developer | `/frontend` | React dashboard |
| Tech Writer | `/docs` | README, API reference, architecture docs |
| Code Reviewer | `/review` | Standards, duplicates, ruff |

See `COMMANDS.md` for the full command reference.

---

## Task Router (automatic specialist selection)

You do **not** need to type `/backend` for every fix. The **Task Router** (`00-task-router.mdc`, always on) uses a **simple 3 + orchestrator** model:

| If task is clearly… | Routes to |
|---------------------|-----------|
| API, LangGraph, LLM, Python bugs | **Backend** · `/backend` |
| React, UI, browser | **Frontend** · `/frontend` |
| Tests, pytest, coverage | **QA** · `/qa` |
| Anything else | **CEO** · `/ceo` or **Sprint** · `/sprint` |

CEO and `/sprint` delegate to the other team members (PO, PM, Architect, DevOps, Security, Docs, Review). You can still invoke them directly with `/devops`, `/security`, etc.

### What you'll see in chat (confidence UI)

The agent **always shows a Routing Card** at the top of the reply before doing work:

```
---
🎯 **Intent:** [what you asked for]
👤 **Specialist:** 🐍 Senior Backend Developer · `/backend`
📋 **Why this specialist:** [plain-English reason]
▶️ **Next step:** [what happens next]
🔗 **Also involved:** [other agents, or none]
---
```

Defined in `.cursor/rules/00-routing-display.mdc`. This is separate from **runtime** note generation progress in the web UI (StatusPanel shows pipeline nodes like "Writing student notes").

**Example:**

```
You: wire retries for Ollama timeouts
     ↓
Chat shows Routing Card → 🐍 Backend · /backend
     ↓
Agent implements

You: fix CI and run security audit
     ↓
Chat shows Routing Card → 🏃 Sprint · /sprint
     ↓
DevOps + Security in chain

You: are we production ready?
     ↓
Chat shows Routing Card → 👔 CEO · /ceo
     ↓
Full audit + assigned work
```

| You want… | Type… |
|-----------|--------|
| Auto-route | Describe the task (no slash command) |
| Explicit routing | `/route <task>` |
| Force one agent | `/backend`, `/qa`, `/frontend`, etc. |
| Full multi-agent cycle | `/sprint` |
|-----------|--------|
| Auto-route + implement | Just describe the task (no slash command) |
| Explicit "who owns this?" | `/route fix gap bridger JSON` |
| Force a specific agent | `/backend`, `/qa`, etc. |
| Full multi-agent cycle | `/sprint` |

Glob rules (e.g. QA when editing `tests/**`) still add standards; the router picks **who leads**.

---

## How a Sprint Works

A sprint is one cycle of work from "project has issues" to "CEO gives a verdict."

```
You type: /sprint
     ↓
CEO reads current state from team_logs/current_status.md
CEO creates a new meeting folder: team_logs/meetings/YYYY-MM-DD_HHMM/
     ↓
Phase 1 — Stabilise code
  /arch   → reviews architecture, produces ADRs
  /backend → fixes all open bugs
  /review  → approves every changed file
     ↓ GATE: Code Reviewer must APPROVE before continuing
Phase 2 — Validate
  /qa       → writes + runs tests, must reach ≥80% coverage
  /security → OWASP + STRIDE audit
     ↓ GATE: QA green + no HIGH security findings
Phase 3 — Ship
  /devops   → Dockerfile + CI
  /frontend → dashboard
  /docs     → README + API docs
     ↓ GATE: Docker builds + CI green
Phase 4 — Close
  /po → acceptance criteria check
  /pm → task board reconciliation
  CEO → final verdict, writes 99_summary.md
     ↓
team_logs/current_status.md updated
```

If a gate fails, the sprint stops. Use `/resume-sprint` to continue from the failed gate without re-running everything.

---

## The Meeting Log

Every sprint creates a meeting folder:

```
team_logs/
├── current_status.md                ← always reflects TODAY's project state
├── production_backlog.md            ← dev workarounds to revert before production
├── runtime_bugs.md                  ← QA → Backend bugs from live/manual runs
└── meetings/
    └── 2026-05-23_0330/             ← Meeting 001
        ├── 00_agenda.md             what this meeting covered
        ├── 01_ceo_report.md         CEO verdict + Assigned Work table
        ├── 02_backend.md            Backend Dev's session log
        ├── 03_qa.md                 QA's session log
        ├── 04_security.md           Security's session log
        ├── 05_devops.md             DevOps's session log
        ├── 06_frontend.md           Frontend's session log
        ├── 07_tech_writer.md        Tech Writer's session log
        ├── 08_code_reviewer.md      Code Reviewer's session log
        ├── 09_architect.md          Architect's session log
        ├── 10_product_owner.md      Product Owner's session log
        ├── 11_project_manager.md    Project Manager's session log
        └── 99_summary.md           ← decisions + checks for NEXT meeting
```

The `99_summary.md` is the most important file. It contains:
- What was decided this meeting
- Every open cross-team flag
- A checklist that gets verified at the START of the next meeting

---

## Runtime QA — Tester Raises Bugs to Developer

Sprint audits and unit tests are not enough. When you **run the app for real** and something breaks, treat it like production QA:

```
You run the app → error in browser or terminal
     ↓
QA logs bug in team_logs/runtime_bugs.md (BUG-RT-###)
     ↓
Backend fixes via /backend or next /sprint
     ↓
QA verifies → mark ✅ in runtime_bugs.md
     ↓
CEO includes open runtime bugs in Assigned Work table
```

**When to log:**
- Any error message shown in the UI
- Any 4xx/5xx in the server terminal during a manual flow
- Flaky behavior (double-click, reload, rate limits)

**Production vs dev workarounds:** Temporary cuts (smaller prompts, lower max_tokens) go in `team_logs/production_backlog.md` — not mixed with bugs. Restore those when Groq Dev tier or a higher-limit provider is available.

## Sprint Work Queue — all backlogs in one place

Every `/sprint` builds a **Sprint Work Queue** in `00_agenda.md` from three sources:

| Source | Always in agenda? | Always executed? |
|--------|-------------------|------------------|
| `runtime_bugs.md` | ✅ | ✅ if open |
| `current_status.md` → v1.1 Backlog | ✅ | ✅ unless you say "bugs only" |
| `production_backlog.md` | ✅ listed | 🟡 deferred until Groq Dev tier |

A sprint that only fixes runtime bugs but ignores v1.1 backlog is **incomplete**. Say **"bugs only"** if you want a narrow sprint.

---

## How Agents Know What to Do

Each agent has two files:

1. **Rule file** (`.cursor/rules/XX-agent-name.mdc`) — deep briefing: what they know about the project, their standards, their checklist, their Go/No-Go criteria. Cursor loads these automatically when globs match or when the Task Router activates them.

2. **Command file** (`.cursor/commands/agent-name.md`) — activation prompt: step into role immediately and start working. Triggered when you type the command **or** when the Task Router selects that agent.

**Task Router** (`.cursor/rules/00-task-router.mdc`) — always on; routes to **Backend, Frontend, QA**, or **CEO/Sprint** (which delegate to everyone else).

---

## The Source of Truth Hierarchy

When an agent is deciding what to do, they read in this order:

```
1. specs/                    original designer's intent (highest authority)
2. team_logs/current_status.md   live project state
3. Previous meeting's 99_summary.md   what was expected this sprint
4. Actual source code        what's really implemented
```

If spec and code disagree → spec wins, flag the gap to Tech Writer.

---

## Quick Reference for Common Situations

| Situation | What to do |
|-----------|-----------|
| Starting fresh session | `/ceo` — see where things stand |
| Not sure which agent | `/route <your task>` — or just describe the task (router auto-picks) |
| Want everything fixed automatically | `/sprint` |
| Previous sprint stopped mid-way | `/resume-sprint` |
| Just want to fix bugs | `/backend` |
| Want to know what happened in past meetings | `/logsummary` |
| Something looks broken architecturally | `/arch` |
| Need to check test coverage | `/qa` |
| Worried about security | `/security` |
| Need to onboard someone new | Share this file + `COMMANDS.md` |
| Error during a live run | Add to `team_logs/runtime_bugs.md`, then `/backend` |
| Remember what to restore for production | `team_logs/production_backlog.md` |

---

## Rules That Keep the System Honest

- **CEO never declares GO** unless QA, Security, and DevOps all pass their hard blockers
- **Agents never mark work done** without evidence in their meeting file
- **Cross-team flags carry forward** until explicitly marked ✅ Resolved
- **Specs are the source of truth** — agents read them before working, not after
- **Meeting folders are never deleted** — they are the audit trail

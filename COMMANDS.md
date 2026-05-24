# Team Command Reference

All commands are typed directly in the Cursor chat. The CEO rule is always active and routes every command to the right agent.

---

## Orchestration Commands

| Command | What it does | When to use |
|---------|-------------|-------------|
| `/route` | Classify a task → activate the right agent — **shows Routing Card in chat** | Unsure who should handle it; explicit routing |
| `/ceo` | Full team audit → production-readiness report with Assigned Work table | Start of any session to see where things stand |
| `/sprint` | Runs all agents with pending work in dependency order automatically | When you want the whole fix cycle done in one go |
| `/resume-sprint` | Picks up a sprint from the last failed gate — skips completed phases | When a previous `/sprint` stopped mid-way |
| `/status` | One-liner status from every agent — fast snapshot | Quick check without a full audit |
| `/logsummary` | Digest of the last 3 meeting summaries | Catch up after time away from the project |

---

## Individual Agent Commands

| Command | Agent | Mandate |
|---------|-------|---------|
| `/po` | Product Owner | Validate spec coverage, flag missing requirements |
| `/pm` | Project Manager | Task board, milestone %, risk register |
| `/arch` | System Architect | Architecture review, produce ADRs |
| `/backend` | Senior Backend Dev | Fix bugs, implement missing features |
| `/qa` | QA Engineer | Write + run test suite, report coverage |
| `/security` | Security Auditor | OWASP + STRIDE scan, veto on HIGH findings |
| `/devops` | DevOps / SRE | Dockerfile, CI/CD, deployment recommendation |
| `/frontend` | Frontend Developer | React dashboard |
| `/docs` | Tech Writer | README, API reference, architecture docs |
| `/review` | Code Reviewer | Standards enforcement, duplicate removal, ruff |

---

## Dependency Order (when running manually)

If you're not using `/sprint`, trigger agents in this order — later ones depend on earlier ones:

```
1. /arch       architecture review first
2. /backend    fixes (needs arch approval)
3. /review     code review (needs backend done)
4. /qa         tests (needs clean, reviewed code)
5. /security   audit (needs qa green)
6. /devops     infra (needs qa passing + security clear)
7. /frontend   UI (needs stable API — can run after step 3)
8. /docs       docs (needs everything settled)
9. /po         acceptance check
10. /pm        task board reconciliation
11. /ceo       final verdict
```

---

## Log & Meeting Commands

| Command | What it does |
|---------|-------------|
| `/logsummary` | Last 3 meeting summaries digest |
| `/ceo` | Also writes CEO report + `99_summary.md` to meeting folder |
| `/sprint` | Creates meeting folder, runs all agents, writes summary |

**Log files location:**
```
team_logs/
├── current_status.md          live project state (always up to date)
└── meetings/
    └── YYYY-MM-DD_HHMM/       one folder per meeting
        ├── 00_agenda.md
        ├── 01_ceo_report.md
        ├── 0X_[agent].md
        └── 99_summary.md      checks for next meeting live here
```

---

## Command Files Location

All command activation prompts live in `.cursor/commands/`:
```
.cursor/commands/
├── route.md
├── ceo.md
├── sprint.md
├── resume-sprint.md
├── logsummary.md
├── po.md
├── pm.md
├── arch.md
├── backend.md
├── qa.md
├── security.md
├── devops.md
├── frontend.md
├── docs.md
└── review.md
```

You can also invoke any agent directly by typing `@.cursor/commands/<name>.md` in chat.

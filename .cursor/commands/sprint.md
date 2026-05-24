# /sprint — Autonomous Fix Cycle

**Activates:** CEO reads current state → triggers all agents with pending work → in dependency order → compiles final verdict

---

## Agent Activation Prompt

You are the **CEO** running a full sprint. Your job is to work through every agent with pending work in the correct sequence. Do not skip steps. Do not run agents in parallel when one depends on the other.

## Step 0 — Read Current State and Resolve Meeting Folder

Before touching any agent:
1. Read `team_logs/current_status.md` — know what's open
2. Read `team_logs/runtime_bugs.md` — all open `BUG-RT-###` items (QA → Backend queue)
3. Read `team_logs/production_backlog.md` — dev workarounds to restore before production (do NOT treat as bugs)
4. Read the latest meeting folder's `99_summary.md` — know what was expected this sprint
5. **Resolve the meeting folder** — use this logic:
   - List all folders in `team_logs/meetings/` sorted newest-first
   - If the newest folder has NO `99_summary.md` → it's an interrupted sprint → use `/resume-sprint` instead, do not create a new folder
   - If the newest folder name starts with today's date (`YYYY-MM-DD`) AND has a `99_summary.md` → today already had a completed sprint → create a new folder with a new timestamp (`YYYY-MM-DD_HHMM`)
   - Otherwise → create a new folder: `team_logs/meetings/YYYY-MM-DD_HHMM/`
6. Write `00_agenda.md` — include **all three work queues** in a single **Sprint Work Queue** table:
7. Write `00_router_log.md` — if the sprint was triggered from a user task (not explicit `/sprint`), record how the task router classified it:

```markdown
# Router Log
- **User request:** [one line]
- **Routed to:** Backend | Frontend | QA | CEO/Sprint
- **Reason:** [one line from task-router decision tree]
- **Delegated via CEO/Sprint:** [agents if any, else —]
```

| # | Source | Item | Owner | Phase | Execute this sprint? |
|---|--------|------|-------|-------|---------------------|
| … | runtime_bugs.md | BUG-RT-### | Backend | 1 | ✅ Always if ⬜/🔄 |
| … | current_status.md → v1.1 Backlog | Task name | Owner from table | 1–3 | ✅ Always unless user says "bugs only" |
| … | production_backlog.md | Restore item | Backend | 1 | ✅ only if Dev tier confirmed; else 🟡 Deferred row |

**Rules for the Sprint Work Queue:**
- **Never run a sprint with only runtime bugs** if v1.1 backlog has open items — both must appear in `00_agenda.md` and `01_ceo_report.md` Assigned Work table
- **Production backlog** — always list every unchecked item; mark 🟡 Deferred with reason if Groq Dev tier unavailable
- If the user did not say "bugs only" or "skip backlog", Backend/DevOps/Frontend **must** pick up their v1.1 items in this sprint

### How all backlogs enter the sprint

| Source file | What it is | When sprint picks it up | Owner in sprint |
|-------------|-----------|-------------------------|-----------------|
| `runtime_bugs.md` | Live-run bugs (BUG-RT-###) | **Every sprint** — all ⬜/🔄 → Sprint Work Queue | Backend → QA verify |
| `current_status.md` → **v1.1 Backlog** | Planned features (SqliteSaver, rate limit, CI…) | **Every sprint** — all rows → Sprint Work Queue | Owner column (Backend, DevOps, etc.) |
| `production_backlog.md` | Dev prompt/token workarounds | **Every sprint listed**; **executed** only when Dev tier / higher TPM confirmed | Backend Phase 1 |

**Priority order (CEO assigns in this order):**
1. Open P0/P1 runtime bugs (`BUG-RT-###`)
2. Open v1.1 backlog items (from `current_status.md`) — **do not skip**
3. Open P2/P3 runtime bugs
4. Production backlog restore — only if tier gate is open (see `production_backlog.md` exit checklist)
5. Remaining v1.1 items if time permits

---

## Sprint Execution Order (strict dependency chain)

```
PHASE 1 — Stabilise the code
  Step 1: /arch      → Review planned fixes for ALL Sprint Work Queue items assigned to Backend
  Step 2: /backend   → Fix: (a) open BUG-RT items, (b) v1.1 backlog items owned by Backend,
                       (c) production_backlog.md ONLY if Dev tier confirmed
  Step 3: /review    → Review every file Backend changed; must APPROVE before QA starts

PHASE 2 — Validate the code
  Step 4: /qa        → Run tests; verify BUG-RT fixes; add tests for v1.1 Backend changes
  Step 5: /security  → Audit fixed code; verify security for v1.1 changes (needs QA green)

PHASE 3 — Ship it
  Step 6: /devops    → Execute v1.1 DevOps items (CI coverage, Docker…) + verify Docker/CI
  Step 7: /frontend  → Execute v1.1 Frontend items if any remain in Sprint Work Queue
  Step 8: /docs      → Update docs for any v1.1 changes shipped this sprint

PHASE 4 — Close the sprint
  Step 9: /po        → Verify acceptance criteria for items shipped this sprint
  Step 10: /pm       → Reconcile Sprint Work Queue — mark ✅ done vs ⬜ carried forward
  Step 11: CEO       → Assigned Work table must show what was ✅ done vs ⬜ deferred
                     → Remove completed items from v1.1 Backlog in current_status.md
                     → Update production_backlog.md checkboxes if restore ran
                     → Update runtime_bugs.md (mark fixed ✅)
                     → Overwrite team_logs/current_status.md
```

## Decision Gates (when to stop the chain)

After each phase, check before proceeding:

| Gate | Check | Fail action |
|------|-------|-------------|
| After Step 3 | Code Reviewer APPROVED all Backend files | Stop — flag to CEO, don't run QA on unapproved code |
| After Step 4 | QA branch coverage ≥ 80%, all P0 tests pass | Stop — flag failures, don't run Security on untested code |
| After Step 5 | Security has no open HIGH findings | Stop — CEO marks NO-GO, sprint ends here |
| After Step 6 | Docker builds + CI green | Stop — don't deploy broken image |

If a gate fails, the CEO writes `99_summary.md` with the failure, marks the sprint status, and stops. The next `/sprint` picks up from the failed gate.

## Skip Logic (don't re-run agents with nothing to do)

Before triggering each agent, check their file from the **current meeting folder**:
- If the file already exists and their verdict is ✅ — skip them, they're done this sprint
- If the file doesn't exist — trigger them
- If the file exists but verdict is ❌ — re-trigger them, they have unresolved work

## Sprint Report Format (CEO writes this at the end)

```
=== SPRINT REPORT ===
Date: [date]
Verdict: ✅ GO / ❌ NO-GO / 🔄 PARTIAL

PHASES COMPLETED
─────────────────
Phase 1 (Stabilise): ✅ / ❌ stopped at Step [N]
Phase 2 (Validate):  ✅ / ❌ stopped at Step [N]
Phase 3 (Ship):      ✅ / ❌ stopped at Step [N]
Phase 4 (Close):     ✅ / ❌

AGENTS ACTIVATED THIS SPRINT
──────────────────────────────
[Agent]   ✅/❌  [one-line result]

GATE FAILURES (why sprint stopped early)
──────────────────────────────────────────
[gate] → [what failed] → [who must fix it]

HARD BLOCKERS RESOLVED THIS SPRINT
────────────────────────────────────
[blocker] → ✅ closed / still open

ASSIGNED WORK FOR NEXT SPRINT
───────────────────────────────
Task / Bug                      Owner           Command
────────────────────────────────────────────────────────
[task]                          [agent]         [/command]
```

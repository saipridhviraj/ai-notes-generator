# /resume-sprint — Resume a Stopped Sprint

**Activates:** CEO reads the last sprint's result, identifies the failed gate, and continues from that exact point — skipping everything already completed.

---

## Agent Activation Prompt

You are the **CEO** resuming an incomplete sprint. Do not re-run agents that already completed successfully this sprint.

## Step 1 — Find the Last Sprint

1. List all folders in `team_logs/meetings/` sorted newest-first
2. Read `team_logs/runtime_bugs.md` — know which BUG-RT items are still open
3. Read `99_summary.md` from the most recent folder
4. Find the section "Checks for Next Meeting" — these are the unresolved items
5. Find which sprint gate failed (look for the gate failure section in `01_ceo_report.md`)

## Step 2 — Assess What's Already Done

Check the current meeting folder for existing agent files:

| File exists + verdict ✅ | → Skip that agent — they're done |
| File exists + verdict ❌ | → Re-run that agent — they have unresolved work |
| File does not exist | → Run that agent — they haven't gone yet |

## Step 3 — Resume from the Failed Gate

```
IF last failure was at Gate 1 (Code Review didn't approve):
  → Re-run: /review → then /qa → /security → /devops → /frontend → /docs → CEO verdict

IF last failure was at Gate 2 (QA failed or coverage < 80%):
  → Re-run: /qa → /security → /devops → /frontend → /docs → CEO verdict

IF last failure was at Gate 3 (Security has open HIGH findings):
  → Re-run: /security → /devops → /frontend → /docs → CEO verdict

IF last failure was at Gate 4 (Docker build / CI failed):
  → Re-run: /devops → /frontend → /docs → CEO verdict
```

## Step 4 — Write the Continued Report

Append to the existing `01_ceo_report.md` in the current meeting folder:

```
## Resume Session — [timestamp]
Resumed from: Gate [N] failure
Agents re-run: [list]
Agents skipped (already ✅): [list]
```

Then write a fresh `99_summary.md` reflecting the updated state.

## Rules
- Never re-create the meeting folder — use the existing one from the interrupted sprint
- Never re-run an agent whose file exists with ✅ verdict — that wastes work
- If the last sprint's `99_summary.md` doesn't exist (sprint was interrupted before CEO wrote it), treat all agents as incomplete and run a full `/sprint` instead

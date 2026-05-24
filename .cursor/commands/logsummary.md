# /logsummary — Last 3 Meetings Summary

**Activates:** CEO reads the last 3 meeting summaries and produces a digest

---

## Agent Activation Prompt

You are the **CEO**. The user wants a digest of the last 3 meetings.

## Steps

1. List all folders inside `team_logs/meetings/` — they are named `YYYY-MM-DD_HHMM`
2. Sort them by name descending — newest first
3. Take the top 3
4. Read the `99_summary.md` file from each of those 3 folders
5. Also read `team_logs/current_status.md` for the live project state
6. Produce the digest below

## Output Format

```
=== LOG SUMMARY — LAST 3 MEETINGS ===
Generated: [date]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MEETING [N] — [folder name] | Verdict: ✅/❌/🔄
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
What happened: [2-3 sentences]
Bugs fixed:    [list or "none"]
Bugs opened:   [list or "none"]
Decisions:     [key decisions made]
Checks for next meeting:
  - [check 1] → ✅ verified / ❌ failed / ⬜ not yet checked
  - [check 2] → ...

[repeat for each of the 3 meetings]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRENT STATUS (live)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Overall: ✅/❌/🔄
Hard blockers open: X
Milestone: M[N] — [name]
Completion: X%

PRIORITY FOR NEXT SESSION
1. [top priority action]
2. [second priority]
3. [third priority]
```

## Rules
- Always verify the "checks for next meeting" from the PREVIOUS summary before reporting
- If a check was supposed to be done but the agent file doesn't exist in the latest meeting, flag it as ⬜ not yet checked
- Never make up status — read the actual files

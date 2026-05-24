# /ceo — Full Team Audit

**Activates:** CEO Orchestrator → coordinates all 10 agents → produces one production-readiness report

## What happens when you run this

The CEO kicks off the entire virtual engineering team in sequence:

1. Product Owner checks spec coverage
2. Project Manager reports task board status
3. System Architect reviews design quality
4. Senior Backend Dev inspects all nodes and known bugs
5. QA Engineer reports test coverage
6. DevOps Engineer checks Docker/CI readiness
7. Frontend Dev reports dashboard status
8. Tech Writer checks documentation completeness
9. Security Auditor scans for vulnerabilities
10. Code Reviewer checks standards and duplicates

## Output

One clean CEO Report:
```
=== CEO PRODUCTION READINESS REPORT ===
Overall Status: ✅ READY / ❌ BLOCKED / 🔄 IN PROGRESS

TEAM FINDINGS
─────────────
Product Owner    ✅/❌/🔄  <summary>
Project Manager  ✅/❌/🔄  <summary>
...

CRITICAL ISSUES
RECOMMENDATIONS
NEXT STEPS
```

## Rule file
→ `.cursor/rules/00-ceo-orchestrator.mdc`

## How to trigger
Type `/ceo` in chat or `@.cursor/commands/ceo.md`

## Related commands
- `/sprint` — runs all assigned agents automatically in dependency order after the CEO report
- `/logsummary` — digest of last 3 meeting summaries

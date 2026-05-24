# /po — Product Owner

**Activates:** Product Owner agent

## Agent Activation Prompt

You are now the **Product Owner** for `ai-notes-generator`. Run your full checklist immediately.

1. Read each of the 8 spec files in `specs/`
2. Cross-reference every promised feature against the actual codebase
3. Flag any gap with priority (P0 = blocks launch, P1 = should fix, P2 = nice to have)
4. Produce your Product Owner Report

## What to check
- All 8 phase specs implemented in source
- `generated_notes/` used for output (not `cwd`)
- Mermaid validators wired into evaluator
- Tutor rejection (`approved: false`) blocks the pipeline
- `error_clarification` field has routing logic
- Gap bridger prompts live in `prompts/` not inline
- Phase 8 E2E smoke test is runnable

## Output format
```
PRODUCT OWNER REPORT
Status: ✅ / ❌ / 🔄
Spec Coverage: X/8 phases fully met

GAPS
- [spec ref] → [what's missing] → [P0/P1/P2]

ACCEPTED
- [verified requirements]
```

## Full briefing
→ `.cursor/rules/01-product-owner.mdc`

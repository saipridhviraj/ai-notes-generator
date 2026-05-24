# /security — Security Auditor

**Activates:** Security Auditor agent

## Agent Activation Prompt

You are now the **Security Auditor** for `ai-notes-generator`. Run a full security scan immediately.

## Scan Sequence

**1. Secrets scan** — check every `.py`, `.yml`, `.json`, `.md` for hardcoded keys
```bash
# Check for accidental key exposure
git log -p | grep -iE "api_key|secret|password|token" | grep -v ".env.example"
```

**2. API security** — read `api/routes.py` and `api/models.py`
- No auth on any endpoint → HIGH risk
- No rate limiting on `/generate` → HIGH risk (open LLM trigger)
- `/tutor/respond/{id}` anyone can approve/reject any session → HIGH risk

**3. Input validation** — read `api/models.py`
- `topic` field: no `max_length` → prompt abuse risk
- `feedback` field: no sanitization → prompt injection risk
- `slug` derived from user input → check path traversal in `file_service.py`

**4. Infrastructure** — check `Dockerfile` if it exists
- Running as root? → add non-root user
- Secrets baked in image? → must be runtime env vars only

**5. Memory** — read `utils/helpers.py`
- Session store has no TTL → memory leak over time

## Known findings (from handoff audit)
| Severity | Location | Finding |
|----------|----------|---------|
| HIGH | `api/routes.py` | No auth on any endpoint |
| HIGH | `api/routes.py` | No rate limiting on `/generate` |
| MEDIUM | `api/models.py` | `topic` has no max_length |
| MEDIUM | `graph/nodes/gap_bridger_node.py` | User feedback injected into LLM prompt |
| LOW | `utils/helpers.py` | Session store has no TTL |

## Output format
```
SECURITY AUDITOR REPORT
Risk Level: HIGH / MEDIUM / LOW
Status: ✅ CLEARED / ❌ BLOCKED / ⚠️ CONDITIONAL

CRITICAL (fix before deploy)
- [finding] [location] [remediation]

WARNINGS
- [finding] [recommendation]

CLEARED
- [check] ✅
```

## Full briefing
→ `.cursor/rules/09-security-auditor.mdc`

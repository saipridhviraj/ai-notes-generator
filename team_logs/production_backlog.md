# Production Backlog — Deferred Quality Changes
> **Purpose:** Track dev/free-tier workarounds vs full production quality.
> **Owner:** Backend Dev | **Implemented:** profile toggle in `services/prompt_config.py`
> **Last updated:** 2026-05-23

---

## Env toggle (one place)

| Variable | Dev (Groq free tier) | Production (Ollama / paid tier) |
|----------|----------------------|----------------------------------|
| `USE_OLLAMA` | `false` | `true` |
| `USE_PRODUCTION_PROMPTS` | auto `false` | auto `true` |
| `PROMPT_PROFILE` | auto `dev` | auto `production` |

**Explicit override:** set `USE_PRODUCTION_PROMPTS=true` on Groq Dev tier, or `USE_PRODUCTION_PROMPTS=false` to test trimmed prompts on Ollama.

**Prompt files:**

| Profile | Location |
|---------|----------|
| Dev | `prompts/profiles/dev/` |
| Production | `prompts/profiles/production/` |

Router: `prompts/student_notes_prompts.py`, `prompts/tutor_notes_prompts.py` → picks profile via `services/prompt_config.py`.

---

## Why This File Exists

During live testing on **Groq free tier**, dev profile reduces prompt size and output limits. Production profile restores full quality — safe on Ollama or higher TPM Groq tiers.

---

## Token & Prompt Reductions (dev vs production)

### 1. Student notes system prompt — few-shot examples
| Field | Dev | Production |
|-------|-----|------------|
| File | `prompts/profiles/dev/student_notes_prompts.py` | `prompts/profiles/production/student_notes_prompts.py` |
| Toggle | `USE_PRODUCTION_PROMPTS=false` | `USE_PRODUCTION_PROMPTS=true` or `USE_OLLAMA=true` |

### 2. Tutor notes system prompt — few-shot examples
| Field | Dev | Production |
|-------|-----|------------|
| File | `prompts/profiles/dev/tutor_notes_prompts.py` | `prompts/profiles/production/tutor_notes_prompts.py` |

### 3. Research data truncated in user prompt
| Dev | Production |
|-----|------------|
| `research_data[:1500]` | Full `research_data` |

### 4. Student notes truncated for tutor prompt
| Dev | Production |
|-----|------------|
| `student_notes[:2500]` | Full `student_notes` |

### 5. Keywords/subtopics capped
| Dev | Production |
|-----|------------|
| `keywords[:6]`, `subtopics[:5]` | All keywords and subtopics |

### 6. max_tokens on note generation nodes
| Dev | Production |
|-----|------------|
| `2048` via `get_note_max_tokens()` | `8192` via `get_note_max_tokens()` |

### 7. Mermaid diagram minimum
| Dev | Production |
|-----|------------|
| 2 diagrams in prompt; validator default 2 | 4 diagrams in prompt; validator default 4 |

### 8. Model mapping (Groq only)
| Dev | Production |
|-----|------------|
| `llama-3.3-70b-versatile` | Confirm latest Groq model when Dev tier opens |

### 9. Rate-limit retry (keep in production)
| Status | ✅ Keep in `services/groq_client.py` |

---

## Production Exit Checklist

- [x] Few-shot examples in separate production prompt files
- [x] No truncation in production profile
- [x] `max_tokens=8192` in production profile
- [x] Minimum 4 Mermaid diagrams in production profile
- [ ] End-to-end run on Ollama completes with production profile
- [ ] QA regression test with production profile

**Command to trigger:** set `USE_OLLAMA=true` or `USE_PRODUCTION_PROMPTS=true` in `.env`

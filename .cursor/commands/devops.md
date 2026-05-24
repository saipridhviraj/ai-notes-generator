# /devops — DevOps Engineer

**Activates:** DevOps Engineer agent

## Agent Activation Prompt

You are now the **DevOps Engineer** for `ai-notes-generator`. Start with your deployment recommendation, then create all infrastructure files.

## Deployment Recommendation (your call)
**Recommended: Google Cloud Run** — stateless FastAPI, scales to zero, fits Google infra, managed HTTPS.
Back it up with reasoning if asked.

## Files to Create

### `Dockerfile`
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p generated_notes
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `docker-compose.yml`
```yaml
version: "3.9"
services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./generated_notes:/app/generated_notes
    restart: unless-stopped
```

### `.github/workflows/ci.yml`
- Trigger on push + PR
- Steps: checkout → setup Python 3.11 → pip install → pytest → docker build
- Use GitHub secrets for `GROQ_API_KEY` and `TAVILY_API_KEY`

## Your Checklist
- [ ] Dockerfile builds cleanly (`docker build .`)
- [ ] `generated_notes/` volume mounted in compose
- [ ] CI runs tests on every push
- [ ] All env vars in `.env.example` documented
- [ ] Health check (`/health`) confirmed in container
- [ ] Deployment steps written for Tech Writer to add to README

## Flag to Architect
- In-memory sessions won't survive container restarts — recommend Redis or Cloud SQL

## Output format
```
DEVOPS ENGINEER REPORT
Deployment Target: Google Cloud Run
Artifacts Created: [list]

BLOCKING ISSUES
- [issue] → [what must happen first]

DEPLOYMENT STEPS (for README)
1. [ordered steps]
```

## Full briefing
→ `.cursor/rules/06-devops-engineer.mdc`

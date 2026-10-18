# AI Tech Consultant Capstone

An MVP containing three AI agents for customer support, email management, and project scoping.

## AI Agents

1. **Knowledge Brain** — A Python/FastAPI service that retrieves information from a local knowledge base, returns source citations, records feedback, and provides a sitemap refresh hook.
2. **Inbox Agent** — A TypeScript/Node.js service that classifies emails, drafts replies, records human edits, and supports human approval.
3. **Meeting-to-Scope Agent** — A Python service that converts meeting transcripts into requirements, estimates, and proposal drafts.

The project uses a human-review approach for customer-facing outputs. Live Claude API calls are optional for local tests. See `DESIGN.md` for architecture, limitations, and future work.

## Technologies

- Python and FastAPI
- TypeScript and Node.js
- Automated tests
- Git

## Prerequisites

- Python 3.11+
- Node.js 20+
- Git
- An Anthropic API key for live Claude calls (optional for tests)

## Run the Project

From the project root, open three separate PowerShell terminals.

### Task 1 — Knowledge Brain

```powershell
cd task1_knowledge_brain
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

API documentation: http://127.0.0.1:8000/docs

### Task 2 — Inbox Agent

```powershell
cd task2_inbox_agent
npm install
npm run dev
```

Service port: 3000

### Task 3 — Meeting-to-Scope

```powershell
cd task3_meeting_scope
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8001
```

API documentation: http://127.0.0.1:8001/docs

### Start All Three Services

From the project root in PowerShell:

```powershell
.\run-all.ps1
```

Check the terminal windows for startup errors.

## Run Tests

Run each command from its task directory.

```powershell
pytest -q
```

For Task 2:

```powershell
npm test
```

## Evaluation and Limitations

`EVALS.md` contains the planned evaluation cases and metrics. Automated test results do not establish live-model quality. The current MVP does not fully implement production-grade sitemap crawling, image understanding, automatic model improvement, or actual email sending.

## Repository

https://github.com/gnaneswar-31/ai-tech-consultant-capstone
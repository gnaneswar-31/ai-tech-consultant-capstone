<<<<<<< HEAD
# AI Tech Consultant Capstone

A beginner-friendly starter implementation of the three-task capstone:
1. **Knowledge Brain** — Python/FastAPI, a small local knowledge store, retrieval, source citations, feedback, and daily sitemap refresh hook.
2. **Inbox Agent** — TypeScript/Node.js, classifies emails, asks the Knowledge Brain for grounded facts, drafts replies, records human edits, and supports approval gates.
3. **Meeting to Scope of Work** — Python multi-agent pipeline that converts transcripts into requirements, estimates, and a proposal; a human must approve output before sharing.

Claude is the central model. API calls are optional for local tests; tests use deterministic mock data and do not require an API key.

> This is an honest MVP/starter, not a claim that production-grade scraping, OCR, embeddings, or self-learning have already been completed. Read `DESIGN.md` for limitations and next steps.

## Prerequisites
- Python 3.11+
- Node.js 20+
- Git
- An Anthropic API key for live Claude calls (optional for tests)

## Quick start

### 1. Configure environment
Copy `.env.example` to `.env` and add your key:
```bash
cp .env.example .env
```
Never commit `.env`. Keep `ANTHROPIC_API_KEY` private.

### 2. Start Task 1
```bash
cd task1_knowledge_brain
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Open http://127.0.0.1:8000/docs. The sample knowledge base is `data/articles.json`.

### 3. Start Task 2
In a second terminal:
```bash
cd task2_inbox_agent
npm install
npm test
npm run dev
```
The TypeScript API listens on port 3000. Set `KNOWLEDGE_API_URL=http://127.0.0.1:8000` in `.env`.

### 4. Run Task 3
```bash
cd task3_meeting_scope
python -m venv .venv
# Activate it, then:
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```
Open http://127.0.0.1:8001/docs.

### 5. Run tests
Task 1:
```bash
cd task1_knowledge_brain
pip install -r requirements.txt
pytest -q
```
Task 2:
```bash
cd task2_inbox_agent
npm install
npm test
```
Task 3:
```bash
cd task3_meeting_scope
pip install -r requirements.txt
pytest -q
```

## Main endpoints
### Task 1
- `GET /health`
- `POST /ingest` — add/update an article
- `POST /ask` — answer a question with citations or abstain
- `POST /feedback` — record human correction
- `POST /refresh` — compare current sitemap URLs with stored article URLs (starter hook)

### Task 2
- `GET /health`
- `POST /draft` — draft a reply, does not send email
- `POST /feedback` — store human-edited draft and feedback
- `POST /approve` — marks a draft approved; this starter intentionally does not connect to an email provider

### Task 3
- `GET /health`
- `POST /scope` — transcript(s) to requirements, estimates, proposal, and change summary
- `POST /approve` — records human approval; it does not send a proposal

## Evaluation honesty
`EVALS.md` includes 20+ cases per task and a measurement template. The tests verify deterministic behavior and safety boundaries; they do not prove live-model quality. Run live-model evals, record actual latency, token usage, API cost, unsupported-answer rate, and human acceptance before reporting scores.

## Git workflow
Make meaningful commits throughout the four days. Example:
```bash
git init
git add .
git commit -m "chore: create capstone structure"
```
Do not fabricate a four-day commit history after the fact. Commit each real milestone as you work.

## Recommended four-day schedule
- Day 1: Knowledge Brain ingestion, retrieval, API and tests.
- Day 2: Inbox Agent, human feedback loop, tests.
- Day 3: Meeting agents, change tracking, tests.
- Day 4: Cross-task integration, model evaluations, README/design, and demo video.
=======
# ai-tech-consultant-capstone
>>>>>>> fc8c0e502817c11a549e26353bc4fead3a220304

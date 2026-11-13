# Private CFO

A personal, privacy-first financial planning assistant for salaried users in India.
You ask questions in a chat. The answers come from your own **confirmed** financial facts
and **deterministic, versioned calculations**. An optional LLM may interpret the question
and explain the result, but it never calculates a number, never sees identity documents,
and cannot change your data.

> **Status:** personal project, not production-ready. Do not use real credentials or real
> financial documents until the release blockers in [docs/README.md](docs/README.md) are
> closed. Nothing here is regulated investment, tax or insurance advice.

Also referred to in code and docs as *ArthaOS*, *Artha* or *Financial Freedom Copilot*.

## Core principles

1. **The model never does the arithmetic.** Every financial value comes from Python `Decimal`
   calculators and is stored as a `CalculationRecord` with inputs, assumptions and a rule version.
2. **Only confirmed facts count.** Entered or extracted values stay *candidates* until you
   confirm them. Replacements keep history.
3. **Identity comes from the server.** Every route uses the authenticated user. A `user_id`
   from the client or the model is never trusted.
4. **Fail closed.** If a regulatory or planning assumption has expired, the calculation is
   refused rather than guessed. Tax answers are currently blocked for this reason.
5. **Documents stay on your device.** The desktop app scans and extracts PDFs locally. Only
   the confirmed structured fact is sent to the server.

## Architecture

```text
 React (Vite) web UI ─┐
                      ├─► FastAPI  /api/auth        sign-in, MFA, refresh tokens
 Tauri desktop app ───┘           /api/v1/agent    conversations, facts, plans
   │                                   │
   │ local only:                       ├─► guardrails (redaction, identity binding,
   │ ClamAV + bubblewrap               │    regulatory language, assumption freshness)
   │ + pdftotext → candidates          ├─► deterministic calculators (Decimal)
   │                                   ├─► optional LLM: plans read-only tool calls /
   ▼                                   │    writes number-free explanations
 confirmed fact only ────────────────► └─► PostgreSQL (SQLAlchemy + Alembic)
```

### How a chat message is handled

`POST /api/v1/agent/conversations/{id}/messages` → `send_message` in
[backend/app/routers/agent_v1.py](backend/app/routers/agent_v1.py):

- **Default path:** [agent_orchestrator.py](backend/app/services/agent_orchestrator.py)
  classifies the intent by keyword, loads confirmed facts from
  [financial_context.py](backend/app/services/financial_context.py), runs a calculator
  ([financial_engine.py](backend/app/services/financial_engine.py),
  [financial_freedom.py](backend/app/services/financial_freedom.py),
  [planning_metrics.py](backend/app/services/planning_metrics.py)) and returns evidence
  blocks. If a model is configured, [model_gateway.py](backend/app/core/model_gateway.py)
  adds an explanation with no figures in it (`store: false`).
- **Conversational path** (`ENABLE_CONVERSATIONAL_AGENT=true`):
  [conversation_requests.py](backend/app/services/conversation_requests.py) →
  [conversation_agent.py](backend/app/services/conversation_agent.py). The model proposes
  read-only tool requests through
  [conversation_gateway.py](backend/app/core/conversation_gateway.py) (OpenAI, with an
  optional local Ollama fallback). The requests are validated and run by
  [conversation_tools.py](backend/app/services/conversation_tools.py).

Retries are idempotent through a per-conversation `client_request_id`. Saving an action
plan requires a single-use confirmation that is bound to the exact payload.

## Repository layout

| Path | Contents |
|---|---|
| `backend/app/auth` | Registration, Argon2id passwords, TOTP MFA, token rotation, lockouts |
| `backend/app/routers` | `agent_v1.py` (mounted). Other routers are feature-flagged and off by default |
| `backend/app/services` | Orchestrators, calculators, planning, proactive reviews, verified memory |
| `backend/app/guardrails` | Redaction, authorization, regulatory language, assumption catalogue |
| `backend/app/models`, `backend/alembic` | SQLAlchemy models and migrations (migrations are authoritative) |
| `backend/tests` | Pytest suite, including safety evaluations and PostgreSQL integration tests |
| `frontend/src` | React UI: `components/ui` (shared), `features/agent` (chat, memory, plans, documents) |
| `frontend/src-tauri` | Rust desktop app for local document scanning and extraction (Linux MVP) |
| `frontend/tests` | Playwright browser journeys (mocked API contracts) |
| `scripts` | Repository, documentation, dependency and assumption-freshness checks |
| `docs` | Design, security, regulatory boundaries and workflows (see status note below) |
| `test-documents` | Synthetic PDFs for testing the desktop document flow |

## Running locally

Requirements: Python 3.12, Node 22, PostgreSQL. For the desktop app you also need Rust,
plus `clamscan`, `bwrap` and `pdftotext` on Linux.

```bash
# 1. Configuration
cp .env.example .env            # set DATABASE_URL; development generates a JWT secret if unset

# 2. Backend (API on http://127.0.0.1:8000)
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/python seed_data.py         # optional: synthetic local accounts
../.venv/bin/uvicorn app.main:app --reload

# 3. Frontend (http://localhost:3000, proxies /api to the backend)
cd frontend && npm ci && npm run dev

# 4. Desktop app (optional)
cd frontend && npm run tauri dev
```

MFA is on by default, so you will be asked to enrol an authenticator app after signing in.
Feature flags and model settings are documented in [.env.example](.env.example). All
optional integrations are off by default.

## Verification

```bash
(cd backend && python -m pytest -q)
(cd frontend && npm run type-check && npm run lint && npm run build)
python scripts/check_documentation.py
python scripts/check_repository_guardrails.py
python scripts/check_assumption_freshness.py
```

`./scripts/install-git-hooks.sh` installs a pre-commit hook that runs
[scripts/verify_changes.sh](scripts/verify_changes.sh). An expired-assumption result is a
real fail-closed outcome. Do not bypass it.

## Deployment

The [Dockerfile](Dockerfile) builds the frontend and serves it from FastAPI.
[render.yaml](render.yaml) defines a paid pilot with managed PostgreSQL.
[render-free.yaml](render-free.yaml) defines a free demo with synthetic data only
([start_demo.py](backend/start_demo.py)). See the
[Render and AWS runbook](docs/workflows/render-pilot-and-aws-migration.md).

## Documentation

Start with [docs/README.md](docs/README.md). It has the authoritative status table:
*implemented*, *partial*, *planned* or *blocked*. Many documents in `docs/` describe the
**target** design. When a document and the code disagree, the code, migrations and tests
win. Contributor and agent rules are in [AGENTS.md](AGENTS.md). Change history is in
[DEVLOG.md](DEVLOG.md).

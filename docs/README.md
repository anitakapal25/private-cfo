# ArthaOS Documentation Index and Current State

**Status:** Authoritative documentation index  
**Last reviewed:** 2026-08-30  
**Next review:** 2026-09-30  
**Owner:** Product and engineering leads

## How to read these documents

Documents in this directory describe either the current implementation or a target
design. A design statement is not evidence that a control exists. Production-readiness
claims require a test, configuration, migration or operational record linked from the
relevant document.

Status terms:

- **Implemented:** present in code and covered by an automated test.
- **Partial:** present but incomplete, simulated or not sufficiently tested.
- **Planned:** target design only.
- **Blocked:** must not be enabled until the named prerequisite is complete.

## Current implementation summary

| Capability | Status | Evidence / limitation |
|---|---|---|
| Chat-first agent UI | Partial | Email/password sign-in, evidence rendering, explicit confirmation, cancellation, idempotent retry, partial-failure and expired-session states pass mocked Playwright browser journeys; streaming and PostgreSQL-backed end-to-end journeys remain pending |
| FastAPI API | Partial | Routes exist; Docker/Render pilot configuration and PostgreSQL readiness checks exist, while deployment evidence and AWS Mumbai migration remain pending |
| Authentication | Partial | Registration, email-verification/reset challenges, Argon2id passwords, TOTP MFA, server-side refresh-token rotation/replay revocation, rate limits and progressive lockouts are implemented. Public registration remains disabled until SMTP delivery, operational monitoring, and PostgreSQL end-to-end evidence are approved |
| Deterministic financial foundation | Implemented | Versioned Decimal net-worth, cash-flow/savings-rate, emergency-fund, debt, goal and financial-freedom calculations have golden, boundary and determinism tests; current tax calculations remain separately blocked by stale rules |
| Verified financial memory | Implemented | Grouped entry records actual monthly values or dated snapshots; matching-period calculations use confirmed facts only, batch confirmation is atomic, and replacement history is preserved and audited |
| Personalized planning actions | Implemented | Product-neutral actions use deterministic impact/ranking; payload-bound single-use confirmation is required before plan persistence |
| Enhanced planning tools | Partial | Agent v1 provides versioned debt metrics, flat cash-flow forecasts, goal progress, user-selected insurance-gap comparisons and confirmed action plans; advanced simulations remain pending |
| Local-only document intelligence | Implemented for Linux MVP; production release gated | Tauri keeps paths and extracted text native, runs ClamAV plus network-isolated bubblewrap/pdftotext, discards one-time selections explicitly or on expiry, and submits only confirmed structured facts with opaque UUID evidence. Server document routes and legacy agent routes are not mounted. A Windows/macOS/Linux package-build workflow is configured, but has not yet produced release evidence; local processing remains Linux-only until platform-specific controls and reviews pass |
| Proactive financial reviews | Implemented | Versioned deterministic rules identify stale facts, negative recurring cash flow, reserve/goal declines and overdue actions; findings are deduplicated, audited and user-controlled, while background scheduling is disabled by default |
| Milestone 7 release validation | Partial | Five browser contract journeys cover the no-upload boundary, cancel/retry, evidence, authorization expiry, partial failure and confirmed plans; CI runs them after build. Real-backend browser journeys, streaming, accessibility automation, migration rehearsal and deployment evidence remain release gates |
| Credential encryption | Partial | Fail-closed Fernet encryption exists; managed KMS and key rotation are pending |
| Account Aggregator | Blocked | Data model is not an RBI-AA integration and must not be represented as one |
| External webhooks | Blocked by default | Requires explicit configuration; production-grade egress control remains pending |
| Phase 3 ecosystem APIs | Blocked by default | Routers are not mounted without capability-specific configuration; provider, consent, privacy and operational release evidence remains pending |
| AI agent | Partial | Phase 1 deterministic agent MVP is implemented with authenticated conversations, persisted runs, tool evidence, safety evaluations and confirmed freedom scenarios. Conversation-scoped cloud-assistance consent and an OpenAI boundary exist, but the external model remains disabled pending provider, privacy and model-release evidence |
| Audit trail | Partial | Agent runs, tool calls, calculations and sanitized audit events are persisted; broader mutation coverage remains pending |
| DPDP operational compliance | Planned | Legal review, notices, consent lifecycle, rights handling and breach workflow are pending |

## Document map

- [Architecture](architecture.md): system boundaries and implementation status.
- [Technology stack](technology-stack.md): current, approved and future technology choices.
- [Domain model](domain-model.md): conceptual business entities.
- [Database model](database-model.md): target schema; migrations remain authoritative.
- [Financial model](financial-model.md): formulas, assumptions and validation requirements.
- [Agent tools](agent-tools.md): target tool contracts and AI safety boundaries.
- [Security](security.md): target controls and current gaps.
- [Threat model](threat-model.md): threats, mitigations and residual risk.
- [Regulatory boundaries](regulatory-boundaries.md): product guardrails; not legal advice.
- [Data governance](data-governance.md): classification, consent, retention, rights and deletion controls.
- [Roadmap](roadmap.md): risk-first implementation sequence.

Operational workflows:

- [Data rights](workflows/data-rights.md)
- [Document ingestion](workflows/document-ingestion.md)
- [Incident response](workflows/incident-response.md)
- [Calculation release](workflows/calculation-release.md)
- [Regulatory update](workflows/regulatory-update.md)
- [Model release](workflows/model-release.md)
- [Ecosystem integration release](workflows/ecosystem-release.md)
- [Codex agent and skill audit](agent-skill-audit.md)
- [Developer workflow and local quality gates](developer-workflow.md)
- [Render pilot and AWS migration](workflows/render-pilot-and-aws-migration.md)

## Required review gates

No real financial documents or credentials may be used until authentication,
authorization, signed desktop distribution, local scanning, temporary-data cleanup,
structured-fact retention/deletion and desktop security controls pass review. Managed
document-storage keys are not required for the approved local-only flow because original
documents are not stored by Private CFO. Personalized investment recommendations and production
Account Aggregator integration require specialist Indian legal/regulatory review.

## Enforceable guardrails

Application guardrails live in `backend/app/guardrails/`:

- `authorization.py`: binds tool inputs to authenticated identity;
- `financial_output.py`: requires calculation traceability metadata;
- `regulatory_language.py`: blocks specific-product and personalized regulated guidance;
- `data_redaction.py`: removes sensitive fields and identifiers at logging/model boundaries;
- `assumption_freshness.py` and `catalog.py`: fail closed on expired rules.

Repository automation lives in `.github/workflows/`. Pull requests run backend,
frontend and repository-policy checks. Separate workflows audit dependencies and
perform scheduled assumption review.

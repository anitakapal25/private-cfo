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
| Chat-first agent UI | Partial | Typed conversation client and evidence rendering build successfully; production sign-in and browser tests remain pending |
| FastAPI API | Partial | Routes exist; no production deployment definition |
| Authentication | Partial | JWT verification and user-bound agent routes exist; rotation, revocation, MFA and rate limits are pending |
| Deterministic calculations | Partial | Calculation tools exist; audit persistence and comprehensive golden tests are pending |
| Document upload | Partial | Size, extension, signature checks and encrypted local storage exist; malware scanning and real extraction are pending |
| Credential encryption | Partial | Fail-closed Fernet encryption exists; managed KMS and key rotation are pending |
| Account Aggregator | Blocked | Data model is not an RBI-AA integration and must not be represented as one |
| External webhooks | Blocked by default | Requires explicit configuration; production-grade egress control remains pending |
| AI agent | Partial | Authenticated v1 conversations, deterministic intent routing, persisted runs and tool evidence exist; external model remains disabled pending its release gate |
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
- [Codex agent and skill audit](agent-skill-audit.md)

## Required review gates

No real financial documents or credentials may be used until authentication,
authorization, encryption-key management, document scanning, retention and deletion
controls pass security review. Personalized investment recommendations and production
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

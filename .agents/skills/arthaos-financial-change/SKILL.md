---
name: arthaos-financial-change
description: Implement or review Private CFO backend calculations, tax, insurance, investment logic, uploaded-document handling, integrations, or financial safety guardrails; not presentation-only UI work.
---

# ArthaOS financial change

Read `AGENTS.md`, `docs/financial-model.md`, `docs/regulatory-boundaries.md`, `docs/workflows/calculation-release.md`, and relevant code in `backend/app/guardrails` before editing. For uploads, also read `docs/workflows/document-ingestion.md`; for external services, read the applicable security and data-governance documents.

Preserve server-owned identity and deterministic calculations. Every financial result must include a calculation ID, assumptions, timestamp, and applicable source/version metadata. Versioned rules require effective and review dates and must fail closed after expiry. Never silently substitute law or rates from memory.

Minimize and redact sensitive inputs, logs, and outputs. Uploaded documents require type and size validation, quarantine and malware-scanning boundaries, and no wholesale transfer to a model. External integrations stay disabled without explicit configuration and require SSRF-safe destinations, encrypted credentials, and separation of public from private data. Block personalized or specific-product regulated guidance at the documented boundary. Add applicable nominal, invalid, boundary, authorization, stale-rule, and traceability tests; calculation and rule changes require the full set.

When delegation is authorized and available, use a bounded subagent for independent financial or security review; strongly prefer this for material user-visible calculation changes.

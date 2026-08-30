# Ecosystem integration release

**Status:** Implemented configuration gate; provider integrations remain blocked  
**Last reviewed:** 2026-08-30

## Purpose

This workflow governs Phase 3 features that disclose data to another person or
organization, accept external events, or connect to a financial-data provider.
All Phase 3 API routers are absent from the running API unless their explicit
configuration gate is enabled.

## Required evidence

Before enabling a capability, record and review:

- product owner and security owner approval;
- purpose, lawful basis, consent and revocation behavior;
- exact data fields transferred and their retention/deletion treatment;
- server-side authorization and cross-user isolation tests;
- audit events that exclude raw financial data and credentials;
- destination allowlisting, authentication, timeout and retry controls;
- incident response, provider outage and credential-rotation procedures;
- regulatory/legal review where the behavior may be regulated.

Financial integrations additionally require a named approved provider and an
internal release-approval reference. These configuration fields are release
evidence, not proof that the provider is RBI-authorized or operational.

## Capability-specific blockers

- **Account Aggregator and investment imports:** select and contract an approved
  provider, implement its real consent protocol, validate authorization and data
  minimization, and pass regulatory review. Existing simulated records are not an
  RBI Account Aggregator integration.
- **Advisor access:** implement client-controlled scope, expiry, revocation,
  advisor-role verification and complete read auditing.
- **Community benchmarks:** document aggregation thresholds and pass
  re-identification and small-cohort tests.
- **Employer wellness:** prove tenant separation and prohibit employers from
  accessing individual financial records without separate explicit consent.
- **Webhooks:** require SSRF-safe destinations, signed delivery, redacted payloads,
  replay protection, bounded retries and a dead-letter process.
- **Exports:** require explicit confirmation, purpose-limited fields, encrypted
  storage, short retention and tested deletion.

## Verification

Default deployments must expose none of the Phase 3 routes. The authenticated
`GET /api/v1/agent/capabilities` endpoint reports only release status and generic
blockers; it never returns provider identifiers, approval references, secrets or
user financial data.

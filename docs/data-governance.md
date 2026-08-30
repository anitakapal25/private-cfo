# Data Governance and Privacy Operations

**Status:** Required control design; operational implementation pending  
**Last reviewed:** 2026-08-30  
**Owner:** Privacy, security and product leads

## Scope

This document covers personal, financial, authentication, document, integration,
telemetry and audit data processed by ArthaOS. It complements the
[regulatory boundaries](regulatory-boundaries.md) and [security architecture](security.md).

## Data inventory requirement

Before production use, maintain a machine-readable record for every data element:

- source and data subject;
- purpose and lawful basis;
- system of record and processors;
- sensitivity classification;
- recipients and cross-border transfers;
- retention trigger and deletion method;
- user rights supported;
- control owner and review date.

## Classification

| Class | Examples | Minimum handling |
|---|---|---|
| Restricted | Credentials, tokens, PAN/Aadhaar fragments, uploaded financial documents | Field/file encryption, least privilege, no application-log content, explicit retention |
| Confidential | Income, expenses, assets, liabilities, goals, extracted fields | Authenticated user-bound access, encryption, access audit |
| Internal | Operational metadata and non-sensitive configuration | Workforce access controls and retention |
| Public | Published educational material | Integrity and source/version controls |

## Current controls and blockers

- Uploaded files and integration credentials use fail-closed application encryption.
- Upload storage location is configuration-driven and local storage is development-only.
- External webhooks and financial integration simulation are disabled by default.
- `.gitignore` excludes environment files and uploads from future Git tracking.
- Existing sample uploads must be treated as test fixtures until their provenance is confirmed.
- Managed KMS, rotation, malware scanning, processor inventory, rights automation and deletion verification are release blockers.

## Retention policy process

Retention periods must be approved per purpose and legal obligation; this document does
not invent universal durations. At minimum define separate schedules for accounts,
financial records, uploaded originals, extracted fields, consent evidence, authentication
events, calculation audit records, webhook deliveries, backups and security logs.

Deletion must cover primary storage, derived data, search indexes, queues, caches and
backup expiry. Legal holds must be documented, scoped and auditable. A user-facing
deletion request is not complete until the workflow records each affected system and its
outcome.

## Consent and rights workflow

1. Present a purpose-specific notice before collection.
2. Record notice version, affirmative action, purpose, timestamp and withdrawal channel.
3. Prevent processing outside the recorded purpose.
4. Make withdrawal as accessible as consent and stop future processing.
5. Support authenticated access, correction, updating, erasure and grievance requests.
6. Propagate valid requests to processors and record completion evidence.

## Incident handling

Maintain a tested playbook joining technical containment, evidence preservation,
DPDP assessment and CERT-In reporting. The applicable notification clocks and content
must be taken from current official rules and directions, with named decision owners and
24-hour contact paths.

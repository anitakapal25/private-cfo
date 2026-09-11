# Conversational Agent Verification Record

**Status:** Offline implementation verified; external-model and production release blocked

**Last reviewed:** 2026-09-11

## Implemented scope

Read-only typed planning, deterministic tool execution, monthly follow-ups, bounded
conversation state, atomic evidence persistence, request replay and concurrent request
protection, a seven-topic official education catalogue, constrained evidence composition,
source/clarification UI, source refresh staging and a budgeted live-evaluation runner.

The model organizes authorized evidence. Free-form generated financial prose, live
rates, product disclosures, broad web search and independent financial/legal review
are not delivered by this implementation.
Requests for uncovered current rates, prices, limits, slabs, and rules fail closed
rather than using the model's memory.

## Verification performed

- Full backend suite, including disposable PostgreSQL acceptance: passed. Includes
  overview, missing facts, period isolation, cross-user access, concurrent retries,
  source controls, and internal runtime cleanup.
- Initial migration through head, plus downgrade/reapply of the conversational
  migration on a disposable PostgreSQL instance: passed.
- Frontend type-check, lint and production build: passed.
- Seventeen mocked-API browser journeys, including new sources and clarification: passed.
- Desktop formatting and Rust regression tests: passed; the installed local document
  pipeline test remains ignored because it requires separate local runtime fixtures.
- Documentation integrity and whitespace checks: passed.
- Live-evaluation runner: dry-run exercised with synthetic pricing inputs; no provider calls.

Backend dependencies emitted deprecation warnings. Browser test logs included a mocked
journey's unsuccessful background proxy request; all assertions passed. Browser journeys
remain mocked API contracts, not full PostgreSQL-backed UI validation.

## Outstanding failures and release gates

The repository guardrail originally reported the existing `.env` file. With explicit
user authorization, it now permits that local file only when Git verifies it is ignored
and untracked; tracked or unignored files and unverifiable Git status still fail.
This is covered by `backend/tests/test_repository_guardrails.py`. The `.env` file
has not been opened, removed, or altered. The tax assumption catalogue remains expired;
its freshness check fails and tax calculations remain blocked. These are not waived.

Live model availability, routing accuracy, provider terms, cost/latency measurements,
independent approvals and production privacy operations remain release gates. The
conversational feature flag remains false in the example configuration. No real
credentials, financial documents, or development database were used for validation.

## Rollout and compatibility

Apply migration `c81a26e09111` before deploying the new application models, even when
the conversation flag is off. This migration was not applied to the user's development
database. Enable the flag only after the [model release workflow](workflows/model-release.md).

Existing conversations start with empty state. A request ID created by the legacy path
cannot be migrated into a new conversational execution safely because its original
payload digest is unavailable; the new path returns a conflict requiring a new ID.
Concurrent busy requests return a retryable conflict. Abandoned reservations can be
reclaimed after a forty-five-second lease. Keep a stable configured JWT secret for
keyed payload-digest comparisons; secret rotation invalidates those digest comparisons.

Disabling the flag restores the existing route. Do not downgrade the database as an
application rollback: the schema is backward compatible, and downgrade removes the
new state/reservation records. The documented downgrade test used disposable data only.

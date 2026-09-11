# Conversational Finance Agent Development

**Status:** Implemented behind a disabled-by-default flag; live-provider and production release gated
**Last reviewed:** 2026-09-11
**Owner:** Engineering and AI safety

## Current behavior

`ENABLE_CONVERSATIONAL_AGENT=false` preserves deterministic keyword routing with an
optional automatic OpenAI explanation. Enabling the flag selects the bounded
conversational service. It works locally with deterministic routing and optionally
uses the configured model to propose typed read-only tool requests. The server
validates and executes requests, then renders authorized evidence. Model composition
selects evidence references; it cannot emit arbitrary financial prose.

The model is configurable through `CONVERSATIONAL_MODEL`, initially `gpt-6-astra`
for evaluation. Availability and fitness must be established by the release runner.
The default is not a claim of successful live-provider validation.

Limits are two planning rounds, eight unique tool calls, one composition call and
thirty seconds, configurable downward. PostgreSQL statements have a separate bounded
timeout. Cancellation is cooperative at checkpoints. A completed result is persisted
and available to retry even if the browser disconnects. Process termination rolls
back evidence; a pending request can be reclaimed after its lease expires.

## Implementation and evidence

- [Orchestration](../../backend/app/services/conversation_agent.py): overview,
  compound requests, local period resolution, validated topic state, partial results.
- [Contracts and registry](../../backend/app/services/conversation_tools.py):
  no SQL, client identity, financial amount arguments, or mutation tools.
- [Behavioral evaluations](../../backend/tests/test_conversation_agent.py) and
  [PostgreSQL acceptance](../../backend/tests/test_conversation_postgres.py).
- [Public catalogue](../../backend/app/services/finance_knowledge.py): brief reviewed
  education for seven topics. This is limited coverage, not unrestricted finance QA.

Current source coverage uses reviewed SEBI education, IRDAI policyholder education,
PFRDA retirement education, and an Income Tax Department filing FAQ. RBI and
EPFO-specific entries remain planned until exact pages and supported claims are
reviewed. Public rates, product disclosures and live prices are not included in this
initial catalogue. No fetched source changes a calculation assumption automatically;
tax calculations remain blocked.
Questions asking for uncovered current rates, prices, limits, slabs, or rules return
an explicit unsupported-coverage result before model invocation.

## Development and review

Preserve existing tracked and untracked work. Use synthetic fixtures and disposable
databases, never the user's development database, credentials or financial documents.
Use existing dependencies. Expand the catalogue through exact official page review,
short original summaries, locator/version metadata and expiry tests.

`python scripts/refresh_finance_sources.py budgeting --output /tmp/artha-source-review`
stages fetched bytes and metadata as pending review. It never changes approved
content. Staged content is untrusted, not passed to the model, and should be removed
by the reviewer after review. Redirects and unapproved destinations fail closed.

Run full repository checks, browser journeys, desktop regression tests, and migrations
against disposable PostgreSQL. `ARTHA_TEST_DATABASE_URL` explicitly enables database
acceptance tests. Ordinary model tests use scripted responses with no API calls.

## Model and privacy release

Automatic assistance follows server configuration and the repository's personal-project
policy; no chat checkbox is required. The new flag does not bypass existing provider
approval/configuration. Pilot, staging and production also require
`CONVERSATIONAL_APPROVAL_REFERENCE`. Reference strings are gating configuration,
not proof of independent review; deployment owners must retain actual evidence.

Send the sanitized current question, validated topic/period state and minimal tool
status evidence. Current planning/composition needs no personal amounts or transcripts.
Use `store: false`; standard provider retention is not Zero Data Retention.
Legacy per-conversation consent endpoints are compatibility records, not switches for
automatic assistance. Update public notices and obtain applicable operational/legal
review before wider deployment.

The opt-in runner `scripts/evaluate_conversation_model.py` uses synthetic cases and
explicit cost bounds. Record results with the model/policy versions and apply
[model release](model-release.md). Passing offline tests alone does not authorize
live deployment. Disable the conversation flag to roll back; disable external model
use to keep conversational deterministic fallback without cloud requests.

## Planned extensions

Free-form grounded paraphrasing, broader official knowledge coverage, dynamic public
web search, richer comparisons, chat mutations, local models and fine-tuning remain
planned. No framework or training pipeline is required for the current implementation.

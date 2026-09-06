# LLM Agent Development Workflow

**Status:** Workflow prepared; conversational LLM implementation planned and release gated  
**Last reviewed:** 2026-09-05  
**Owner:** Engineering and AI safety leads

## Objective and current boundary

Use an LLM to interpret questions and draft replies while authenticated application
tools remain the authority for financial values and mutations. The current optional
gateway only explains previously selected evidence; it is not a conversational
tool-calling agent. Hosting and provider selection remain unresolved. This workflow
does not enable a model, approve a provider, or claim production readiness.

## Isolated development

Use branch `feat/llm-agent` in the sibling `private-cfo-llm-agent` worktree. Preserve
the original workspace. Transfer only the explicitly reviewed tracked-file diff
using a binary patch, compare the resulting diff byte-for-byte, and commit that
baseline separately. Do not copy environment files, credentials, financial documents,
databases, or generated artifacts. Install dependencies from the existing lockfiles.
Use synthetic fixtures and a separate disposable test database; never run seed/reset
operations against the development user's database. Repository hooks still apply.

## Implementation sequence

1. **Tool contracts:** wrap existing deterministic functions with typed inputs and
   results, missing-field and period information, calculation references, assumptions,
   versions, and provenance. Inject identity server-side. Allowlist tools and arguments;
   prohibit arbitrary database queries and model-provided ownership. Audit every call.
2. **Bounded orchestration:** introduce a provider-neutral adapter and scripted fake.
   Validate model tool requests before execution. Bound rounds, calls, output size,
   elapsed time, and retries in configuration. Explicitly choose and test these bounds
   before implementation is accepted. Preserve existing confirmation requirements.
3. **Response composition:** supply only authorized evidence. Draft financial values
   as typed evidence references resolved by the server. Reject unknown references,
   unsupported numerical claims, and regulated product advice. Any derived financial
   value requires a tool. Validate qualitative claims against the supplied evidence too.
4. **Conversation state:** retain bounded, server-owned topic and pending-input state.
   Resolve follow-ups and explicit topic changes. Treat chat-supplied amounts as
   unverified candidates; use existing confirmation before financial calculations.
5. **Consent and hosting:** choose local or cloud hosting and document the actual
   data flow. For cloud, version the purpose, notice, data categories, provider and
   retention terms. Existing explanation-only consent excludes raw messages and is
   insufficient for conversational processing. Require fresh consent before sending
   sanitized questions or bounded conversation context. Redact identifiers locally;
   exclude documents, extracted text, paths, credentials and unauthorized records.
6. **Chat integration:** present progress, partial results, focused clarification,
   evidence and cancellation. Preserve request idempotency. On model failure, return
   a deterministic explanation of completed results without inventing missing values.

## Evaluation and acceptance

Ordinary PR tests use synthetic data and scripted/mocked model responses, no provider
credentials or network calls. The preparation tests in
`backend/tests/test_llm_agent_preparation.py` expose existing routing gaps as strict
expected failures; they are not proof of implemented LLM behaviour. The adjacent
evaluation-case catalogue specifies future acceptance scenarios, including missing
data, multi-turn context, fake model figures and repeated request IDs.

Implement runtime integration assertions for every catalogue case as its stage lands.
Remove the corresponding expected-failure marker when behaviour is implemented.
Release acceptance requires no outstanding expected failures or catalogue-only cases,
cross-user isolation, fail-closed stale rules, evidence for every financial result,
and bounded deterministic fallback. A passing catalogue schema test alone is not a
behavioural evaluation.

Reuse the existing PR backend/frontend jobs. Keep backend, frontend and desktop
verification intact. Run documentation and repository checks for preparation changes.
For implementation, run the full repository verification, plus assumption freshness;
expiry is a release failure, not a reason to bypass a check.

Live-provider evaluation is a later manual release gate using synthetic data, an
approved provider, explicit cost limits, and versioned model/prompt/tool artifacts.
Add a manually triggered workflow only after an executable evaluation runner exists;
never expose provider credentials to PR code. Apply the
[model release workflow](model-release.md) before enabling external execution.
Monitor sanitized outcome codes, latency, fallback frequency and safety violations;
retain a kill switch that restores deterministic responses.

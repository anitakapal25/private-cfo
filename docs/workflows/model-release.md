# Model, Prompt and Tool Release Workflow

**Status:** Required release procedure; conversational live-provider approval pending
**Last reviewed:** 2026-09-11
**Owner:** AI safety and product

## Current implementation and policy

The application supports optional automatic explanations and a separately flagged
read-only conversational planner. Both require configured provider eligibility.
Conversational planning accepts typed requests; financial arithmetic and persisted
facts remain application-owned. Composition accepts authorized evidence references
only. See [development workflow](llm-agent-development.md) for exact runtime limits.

This personal project uses server-controlled automatic assistance with `store: false`.
Legacy conversation-consent APIs do not gate automatic execution. Standard provider
retention terms apply; do not claim Zero Data Retention or completed privacy operations.

## Mandatory evidence before enablement

1. Record the model, prompt, tool, source and policy versions plus allowed data fields.
2. Run offline evaluations for tool authorization, cross-user isolation, period handling,
   missing facts, injection, numerical fabrication, unknown references and stale rules.
3. Run PostgreSQL retry/concurrency and migration acceptance, frontend browser journeys,
   and existing backend/frontend/desktop checks. Explain every outstanding failure.
4. Review actual provider data handling and operational notices. Preserve the no-document,
   no-path, no-credential and product-neutral boundaries.
5. Run the opt-in synthetic live evaluation with an explicit budget. Retain sanitized
   results; inspect semantic routing errors, latency and model compatibility.
6. Obtain an actual versioned approval record before setting release references and flags.
7. Roll out gradually. Monitor sanitized tool outcomes, fallback frequency, source misses,
   response latency and validation rejections. Exercise the rollback flag.

## Acceptance limits

A passing JSON schema is not proof that a selected tool answers the user's question.
Review representative conversational tasks and incorrect-but-valid tool selections.
The current model cannot add arbitrary prose: the server resolves evidence references
and renders deterministic explanations. More expressive composition needs additional
claim-grounding evidence before release.

Source review and tax-rule approval are separate. Reading a current official page
cannot enable an expired calculator. Real financial documents and credentials remain
subject to the blockers in the [documentation index](../README.md).

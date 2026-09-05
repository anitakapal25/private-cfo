# Model, Prompt and Tool Release Workflow

**Status:** Required before enabling an external LLM  
**Last reviewed:** 2026-09-05
**Owner:** AI safety and product leads

1. Define allowed intents, prohibited actions, data fields and tool permissions.
2. Verify that authenticated identity is injected server-side and unavailable for model override.
3. Restrict tools with typed schemas, least privilege and per-resource authorization.
4. Run prompt-injection, data-exfiltration, regulated-advice and tool-confusion evaluations.
5. Verify that every financial number originates from a validated deterministic tool result.
6. Test refusals, uncertainty, stale assumptions and low-confidence document data.
7. Review provider data handling, retention, training use and regional processing terms.
8. Approve a versioned model/prompt/tool bundle and deploy gradually.
9. Monitor safety metrics and maintain immediate rollback and kill-switch capability.

## Conversational agent acceptance gates

The [development workflow](llm-agent-development.md) is prepared; the conversational
LLM and its live-provider evaluation runner remain planned. Existing cloud consent
authorizes evidence explanation and excludes raw messages. Do not reuse it to send
questions or conversation history: approve a versioned notice, minimized fields,
retention terms and renewed consent for the expanded purpose first.

Before release, record executable evidence for each gate:

- Tool requests reject unknown names, invalid arguments, ownership overrides and
  unconfirmed mutations; every executed tool has an audit record.
- All displayed financial values resolve to authorized deterministic evidence.
  Fabricated numbers, unknown references and unsupported claims fail validation.
- Prompt injection, data exfiltration and tool-confusion cases fail closed across
  questions, conversation context and tool output.
- Product-selection paraphrases, including combined product categories, receive a
  useful boundary response; safe educational questions remain answerable.
- Missing or period-incompatible data produces focused questions and partial
  evidence where possible; unverified statements cannot become calculation inputs.
- Timeouts, malformed responses and exhausted call budgets yield bounded fallback.
  Retries do not duplicate calculations, messages, confirmations or mutations.
- Multi-turn state and consent remain isolated by authenticated user/conversation;
  revoked or outdated consent prevents further cloud disclosure.

Offline CI uses synthetic fixtures and mocked adapters. Known expected failures and
catalogue-only scenarios are outstanding release work, even when PR CI is green.
Run live-provider evaluations manually only after provider/privacy approval and an
evaluation runner exist. Capture model, prompt, tool and policy versions, pass/fail
results, approved cost limits and rollback evidence without sensitive transcripts.

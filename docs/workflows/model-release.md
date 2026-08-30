# Model, Prompt and Tool Release Workflow

**Status:** Required before enabling an external LLM  
**Last reviewed:** 2026-08-30  
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

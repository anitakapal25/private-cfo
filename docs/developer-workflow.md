# Developer Workflow and Local Quality Gates

**Status:** Implemented  
**Last reviewed:** 2026-09-01  
**Next review:** 2026-10-01  
**Owner:** Engineering

## Local hooks

Run the following once after cloning the repository:

```bash
./scripts/install-git-hooks.sh
```

The versioned pre-commit hook runs `scripts/verify_changes.sh`. It fails the commit
when any of these checks fail:

- repository secret and unsafe-route guardrails;
- Markdown documentation integrity;
- dependency health: registry-reported deprecated JavaScript packages, unpinned Python requirements and deprecated Pydantic model configuration;
- backend tests;
- frontend linting, type checking, production build and Playwright browser journeys;
- desktop formatting and Rust tests.

The browser journeys are the UI gate. They cover sign-in, local-only document
boundaries, cancelled/retried requests, expired authorization, partial failures and
explicit plan confirmation.

The hook verifies the working tree, not only staged files. Resolve or intentionally
separate unrelated local changes before committing.

## Release-only checks

The local hook does not run the financial-assumption freshness check. That check is
run in scheduled CI and must be reviewed using the [regulatory update workflow](workflows/regulatory-update.md).
It is fail-closed when a rule is expired; developers must not bypass it to unblock a
feature commit.

CI also runs vulnerability audits (`pip-audit`, `npm audit`) and dependency review for
pull requests. A clean deprecation check does not replace vulnerability triage or
provider compatibility review.

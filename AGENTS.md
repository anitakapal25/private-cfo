# Private CFO repository instructions

Private CFO is a privacy-first financial planning application for Indian users. Treat financial, identity, and uploaded-document data as sensitive.

## Non-negotiable boundaries

- Financial values shown to users must come from deterministic application tools, never model arithmetic or invented estimates.
- Bind access to the authenticated server-side identity. Never trust a client- or model-supplied `user_id` for authorization.
- Fail closed when a regulatory assumption is expired, unreviewed, or missing.
- Do not present personalized investment, insurance, or tax recommendations as regulated professional advice.
- Redact credentials, tokens, PAN, Aadhaar, and document contents from logs, model boundaries, and user-facing exceptions.
- Code, migrations, and tests are implementation evidence. Documentation must distinguish implemented, partial, planned, and blocked behavior.
- Do not use real credentials or financial documents until the security release blockers documented in `docs/README.md` are closed.

Read `docs/README.md` before cross-cutting work. Read the applicable documents in `docs/workflows/` and `backend/app/guardrails/` before financial, security, or data-handling changes.

## Structure and safety

- Backend: `backend/app`; tests: `backend/tests`.
- Frontend: `frontend/src`; reusable UI belongs in `components/ui`, feature code in `features/<feature>`.
- Guardrails: `backend/app/guardrails`; repository checks: `scripts/`; CI: `.github/workflows`.
- Preserve unrelated work. Prove static, dynamic, configuration, test, and documentation references before declaring a file unused.
- Do not add a dependency when the existing stack reasonably handles the task.

## Verification

Use checks proportional to the change. Full verification is:

```bash
(cd backend && python -m pytest -q)
(cd frontend && npm run type-check && npm run lint && npm run build)
python scripts/check_documentation.py
python scripts/check_repository_guardrails.py
python scripts/check_assumption_freshness.py
```

An expired-assumption failure is a real fail-closed result. Do not bypass it.

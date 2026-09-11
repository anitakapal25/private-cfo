# Private CFO repository instructions

Private CFO is a personal, privacy-first financial planning project for Indian users. Treat financial, identity, and uploaded-document data as sensitive.

## Non-negotiable boundaries

- Financial values shown to users must come from deterministic application tools, never model arithmetic or invented estimates.
- Bind access to the authenticated server-side identity. Never trust a client- or model-supplied `user_id` for authorization.
- Fail closed when a regulatory assumption is expired, unreviewed, or missing.
- Do not present personalized investment, insurance, or tax recommendations as regulated professional advice.
- When users ask which mutual fund, stock, or other investment product to choose, provide useful decision support instead of a generic refusal. Explain relevant product categories, current official disclosures, comparison criteria, risks, costs, liquidity, diversification, and trade-offs. Use deterministic tools for every financial calculation and dated authoritative sources for current claims. The LLM may interpret questions and draft explanations, but it must not invent figures, automatically create a personalized product shortlist, rank a product as "best," or issue buy/sell instructions. Invite the user to select products for a neutral comparison and refer requests for final personalized recommendations to an appropriately SEBI-registered adviser.
- Redact credentials, tokens, PAN, Aadhaar, and document contents from logs, model boundaries, and user-facing exceptions.
- Code, migrations, and tests are implementation evidence. Documentation must distinguish implemented, partial, planned, and blocked behavior.
- Do not use real credentials or financial documents until the security release blockers documented in `docs/README.md` are closed.

Read `docs/README.md` before cross-cutting work. Read the applicable documents in `docs/workflows/` and `backend/app/guardrails/` before financial, security, or data-handling changes.

## LLM-assisted replies

- In configured deployments, use the LLM automatically for eligible requests without requiring a chat checkbox.
- Keep deterministic local evidence authoritative. The separately flagged conversational LLM may propose validated read-only tool requests and organize evidence; it must never supply financial arithmetic or mutation authority.
- Send only the sanitized current question, bounded validated topic/period state, intent-relevant verified financial memory when necessary, and authorized deterministic evidence to the model.
- Do not send personal financial memory for stock or fund selection requests. Keep their decision support product-neutral.
- Never send PAN, Aadhaar, credentials, account identifiers, unverified facts, document contents, or file paths across the model boundary.
- Every financial value must originate from deterministic application tools, never from model arithmetic or invention.
- Set `store: false` on OpenAI requests. This personal project may use the configured OpenAI API under its standard provider retention terms; do not represent it as Zero Data Retention unless that approval exists.
- If configuration or retention approval is missing, or the model request fails, times out, or produces unsafe output, return the local response without a cloud-failure warning. When an assumption is stale, preserve the required fail-closed local response.
- Private CFO may retain conversation history and sanitized audit records under the repository's data-governance rules.
- The model must never rank a product as "best," create a personalized product shortlist, invent figures, or issue buy/sell instructions.

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

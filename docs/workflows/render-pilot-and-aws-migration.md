# Render Pilot and AWS Migration Runbook

**Status:** Deployment configuration implemented; deployment and approvals pending
**Last reviewed:** 2026-09-01
**Next review:** 2026-10-01
**Owner:** Engineering, security, privacy and operations leads

## Render pilot boundary

### Separate free synthetic demo

`render-free.yaml` defines a free web service and free PostgreSQL database for
synthetic testing only. It does not replace the paid real-user pilot below.
`backend/start_demo.py` runs migrations at startup (free services do not use the
paid pre-deploy step), creates one non-admin `demo@example.com` account, preserves
MFA, and forces external models, integrations, email and public registration off.
Use the Render-generated `DEMO_PASSWORD` from the service's Environment page to
sign in, then enroll an authenticator. Never put real financial data in this demo.
Existing accounts/passwords are not reset at restart. Startup isolation is covered
by `backend/tests/test_demo_startup.py`.

Render's free database expires after 30 days and has no backups. Free web services
sleep after inactivity. Keep the workspace without a payment method to avoid
usage overage charges; do not upgrade compute plans. See
[Render free limits](https://render.com/docs/free). Deployment evidence remains
pending until the service has built and its readiness endpoint passes.

`render.yaml` provisions the Singapore pilot API and a paid PostgreSQL database. The
free database tier is prohibited because it has no managed backup or recovery
capability. The pilot must not
be deployed until the privacy owner approves the public privacy notice, Singapore
processing disclosure, data-rights process, incident contacts and retention schedule.

The pilot stores only authenticated account data, consent records, audit records and
explicitly confirmed structured financial facts. Original documents, paths, raw
extracted text and local indexes remain on the user's device. External model use is
off by default and cannot be enabled without the required provider review, secret and
release-approval reference.

Before launch, record the custom domain, TLS owner, backup configuration, recovery
objective, monitoring destination, incident contacts and rollback owner outside source
control. Do not put credentials, keys, approval references or user data in this file.

## AWS Mumbai migration

1. Provision isolated AWS Mumbai application, PostgreSQL, KMS, secrets, monitoring and
   backup resources from reviewed infrastructure definitions.
2. Restore a scrubbed rehearsal backup into a non-production environment and verify
   migrations, account isolation, calculations, consent revocation, health checks and
   data-rights requests.
3. Schedule maintenance, stop writes, create an encrypted final backup and verify its
   checksum before transfer.
4. Restore into AWS, rotate application and database secrets, run migrations and
   execute the production smoke suite against the custom domain.
5. Cut DNS only after health, login, deterministic calculation and rollback checks
   pass. Keep Render read-only until the agreed rollback window closes.
6. Record the migration evidence, then delete Render databases, backups and secrets
   according to the approved retention/deletion record. Verify deletion without copying
   financial values into tickets or logs.

## Release blockers

- Public registration is disabled by configuration. Email verification, password reset,
  refresh-token rotation/revocation, rate limiting, progressive lockout and TOTP MFA
  are implemented, but SMTP delivery, operational monitoring and PostgreSQL-backed
  end-to-end security evidence are required before public sign-up is enabled.
- Data-rights requests, retention/deletion propagation, the public privacy notice,
  grievance contact and incident-contact operations are documented workflows, not yet
  production APIs or operational evidence.
- No signed Windows, macOS or Linux installer may be distributed without the relevant
  platform signing identity and independent desktop security approval.
- The current local document processor is Linux-only. Windows and macOS builds must
  keep document review unavailable until their fail-closed scan, isolation, cleanup and
  review evidence is complete.
- Current tax calculations remain blocked until the expired rule catalogue completes
  the [regulatory update workflow](regulatory-update.md).
- No approved public-information provider or source licence is configured. The source
  adapter therefore remains disabled, and no current tax, stock or bank-rate answer
  may be presented as live information.
- External-model consent and the OpenAI adapter are implemented but the feature is
  disabled. Prompt-injection, data-exfiltration, refusal and deterministic-traceability
  evaluations, provider approval and operational monitoring are still required.
- Account Aggregator, personal bank imports, advisor sharing, exports and webhooks
  remain disabled for the pilot.

## Public agent registration configuration

Registration is shared by browser and desktop clients through the same API and
PostgreSQL database. The capability endpoint (`GET /api/auth/capabilities`) exposes
only account-action availability. Registration requires verified email followed by
password sign-in and authenticator enrollment; existing users provide their MFA code.
Lost or expired verification links can be replaced through the rate-limited
`POST /api/auth/verification/resend` endpoint. Failed delivery preserves the old link.

Configure the regular server environment, never source-controlled credentials:

```dotenv
ENABLE_PUBLIC_REGISTRATION=true
ENABLE_MFA=true
EMAIL_DELIVERY_MODE=smtp
SMTP_HOST=<existing-provider-host>
SMTP_PORT=587
SMTP_SECURITY=starttls
SMTP_USERNAME=<provider-username>
SMTP_PASSWORD=<provider-password>
EMAIL_FROM_ADDRESS=<verified-sender-address>
PUBLIC_APP_URL=https://<public-agent-origin>
ENCRYPTION_KEY=<valid-Fernet-key>
JWT_SECRET=<stable-random-secret-at-least-32-characters>
```

Use the provider's existing SSL/port settings if different. `PUBLIC_APP_URL` must
be an HTTPS origin with no credentials, query, fragment or subpath. Loopback HTTP
is accepted only in development/test. The origin must serve `/verify-email` and
`/reset-password` through the frontend, connected to this same API. Never rotate
an existing encryption key without migrating encrypted MFA secrets.

Browser builds use same-origin API requests. For packaged desktop builds, set
`VITE_API_ORIGIN=https://<public-agent-origin>` when building, and merge that exact
origin into the Tauri `app.security.csp` connect-src directive using a deployment
config passed to `npm run tauri -- build --config <deployment-config.json>`.
Preserve the other CSP directives; do not allow wildcard destinations. The backend
allows only the built-in Tauri origins for cross-origin GET/POST requests, with
Authorization and Content-Type headers. Email verification opens in the browser;
users then return to the desktop agent and sign in. No deep link is needed.

Before public activation, record successful SMTP delivery using an approved test
account, monitoring/incident ownership, and PostgreSQL authentication journey
results. Run migrations before restarting the regular server. Verify capability
availability, registration, resend, verification, MFA enrollment, subsequent login,
password reset and logout. Test fixtures intercept SMTP and are not proof of live
provider delivery. Keep existing privacy and real-data release gates open until
reviewed; the free demo continues to force registration off.

For local regression testing, build the frontend, install the Playwright browser (or use installed Chrome), migrate a disposable PostgreSQL database and run:

```bash
ARTHA_TEST_DATABASE_URL=<disposable-postgresql-url> ARTHA_BROWSER_AUTH_TEST=1 python -m pytest backend/tests/test_registration_postgres.py -q
(cd frontend && npm run test:e2e -- mfa-setup.spec.ts)
```

Rollback public enrollment by setting `ENABLE_PUBLIC_REGISTRATION=false` and
restarting the server. Preserve SMTP, MFA and encryption keys so existing users
can still sign in and reset passwords.

## Brevo Free for small-scale local testing

The existing SMTP adapter supports Brevo without a new dependency. Select the Free
plan in Brevo, enable transactional sending if account activation is requested,
and add/verify your sender under Senders. Brevo may rewrite free-address senders
onto a Brevo domain; inspect the sender status before testing.

Copy the SMTP login and create an SMTP key under **Settings > SMTP & API**.
The SMTP login is different from your account email; the SMTP key is different
from an API key. Store both directly in the ignored root `.env`, never in chat.

```dotenv
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_SECURITY=starttls
SMTP_USERNAME=<Brevo-SMTP-login>
SMTP_PASSWORD=<Brevo-SMTP-key>
EMAIL_FROM_ADDRESS=<sender-verified-in-Brevo>
PUBLIC_APP_URL=http://localhost:3000
ENABLE_MFA=true
EMAIL_DELIVERY_MODE=smtp
ENABLE_PUBLIC_REGISTRATION=true
```

Until credentials are configured, keep `EMAIL_DELIVERY_MODE=disabled` and
`ENABLE_PUBLIC_REGISTRATION=false`. Restart the backend after changing settings;
it caches configuration. An existing unverified account should use **Resend
verification email**, rather than registering again. Inspect Brevo transactional
logs and the recipient inbox/spam folder to confirm delivery. Free-plan limits are
provider-enforced; this application does not provision or upgrade a Brevo plan.

This setup does not establish live-delivery evidence or waive the existing
real-data release gates. Local links work on the development computer; remote
users require the public HTTPS origin.

Provider setup: https://help.brevo.com/hc/en-us/articles/7924908994450-Send-transactional-emails-using-Brevo-SMTP

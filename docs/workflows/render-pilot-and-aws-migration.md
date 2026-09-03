# Render Pilot and AWS Migration Runbook

**Status:** Deployment configuration implemented; deployment and approvals pending
**Last reviewed:** 2026-09-01
**Next review:** 2026-10-01
**Owner:** Engineering, security, privacy and operations leads

## Render pilot boundary

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

# Codex Agent and Skill Audit

**Status:** Current repository automation assessment  
**Last reviewed:** 2026-08-30

Claude-specific static agents and commands were replaced by root `AGENTS.md`
instructions and four focused repository-local Codex skills. Codex subagents are
delegated dynamically for bounded work instead of being stored as persistent role
files.

| Codex skill | Purpose | Assessment |
|---|---|---|
| `arthaos-financial-change` | Financial logic, private data paths, integrations, and guardrails | Required for high-risk product changes |
| `arthaos-react-ui` | Design system, React implementation, API integration, and visual QA constraints | Useful and appropriately scoped |
| `arthaos-review` | Security, documentation, financial-model, and release verification | Useful; read-only unless fixes are requested |
| `safe-repository-cleanup` | Evidence-based cleanup and approved deletion | Required for safe repository maintenance |

The previous `setup-todos` command was not migrated. It assumed every session
needed database seeding, migrations, and server startup, and contained stale
project behavior. General repository boundaries belong in `AGENTS.md`; executable
controls remain in `backend/app/guardrails`, scripts, tests, and CI workflows.

The migration deliberately preserves the fail-closed expired tax assumption,
security-boundary tests, operational runbooks, and production-blocker disclosures.

"""Fail-closed status reporting for Phase 3 ecosystem capabilities."""

from dataclasses import asdict, dataclass

from app.core.config import Settings


@dataclass(frozen=True)
class CapabilityStatus:
    status: str
    reason: str


def get_ecosystem_capabilities(settings: Settings) -> dict[str, dict[str, str]]:
    """Return non-sensitive release status; configuration never implies provider health."""

    def configured(enabled: bool, disabled_reason: str) -> CapabilityStatus:
        if enabled:
            return CapabilityStatus(
                status="configured_not_verified",
                reason="Enabled by configuration; runtime and release verification are still required.",
            )
        return CapabilityStatus(status="disabled", reason=disabled_reason)

    capabilities = {
        "advisor_access": configured(
            settings.enable_advisor_access,
            "Disabled until consent, role, privacy, and audit release checks pass.",
        ),
        "account_aggregator_and_investment_platforms": configured(
            settings.enable_financial_integrations,
            "Blocked until an approved provider and release approval reference are configured.",
        ),
        "community_benchmarks": configured(
            settings.enable_community_benchmarks,
            "Disabled until anonymization and re-identification-risk checks pass.",
        ),
        "employer_wellness": configured(
            settings.enable_wellness_programs,
            "Disabled until employer data-separation and consent checks pass.",
        ),
        "external_webhooks": configured(
            settings.enable_external_webhooks,
            "Disabled until destination allowlisting, signing, retry, and redaction checks pass.",
        ),
        "financial_data_exports": configured(
            settings.enable_data_exports,
            "Disabled until confirmation, minimization, retention, and deletion checks pass.",
        ),
    }
    return {name: asdict(value) for name, value in capabilities.items()}

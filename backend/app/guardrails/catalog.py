"""Reviewed assumption catalogue. Entries must use authoritative sources."""

from datetime import date

from app.guardrails.assumption_freshness import VersionedAssumption


TAX_RULES_FY_2023_24 = VersionedAssumption(
    identifier="india-income-tax-fy-2023-24",
    effective_from=date(2023, 4, 1),
    review_by=date(2024, 3, 31),
    source_url="https://www.incometax.gov.in/",
)

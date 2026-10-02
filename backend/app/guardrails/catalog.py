"""Reviewed assumption catalogue. Entries must use authoritative sources."""

from datetime import date
from decimal import Decimal

from app.guardrails.assumption_freshness import VersionedAssumption


TAX_RULES_FY_2023_24 = VersionedAssumption(
    identifier="india-income-tax-fy-2023-24",
    effective_from=date(2023, 4, 1),
    review_by=date(2024, 3, 31),
    source_url="https://www.incometax.gov.in/",
)


# Neutral planning baselines. These are scenario inputs, not market forecasts or
# personalized recommendations. Financial-model owners must review and extend the
# review window through the calculation-release workflow.
FINANCIAL_FREEDOM_INFLATION = VersionedAssumption(
    identifier="financial-freedom-inflation-baseline",
    value=Decimal("0.0600"),
    version="2026-10-02",
    effective_from=date(2026, 10, 2),
    reviewed_at=date(2026, 10, 2),
    review_by=date(2026, 12, 31),
    source_url="https://egazette.gov.in/WriteReadData/2026/271285.pdf",
    methodology="Illustrative conservative scenario using the upper 6% tolerance of India's 2026-31 inflation target; not an inflation forecast. Household inflation can differ.",
)

FINANCIAL_FREEDOM_RETURN = VersionedAssumption(
    identifier="financial-freedom-product-neutral-return-baseline",
    value=Decimal("0.0800"),
    version="2026-10-02",
    effective_from=date(2026, 10, 2),
    reviewed_at=date(2026, 10, 2),
    review_by=date(2026, 12, 31),
    source_url="https://investor.sebi.gov.in/calculators/Assets_Allocations.html",
    methodology="Internal product-neutral illustrative input. SEBI's calculator permits user-entered expected returns but does not endorse 8%; this is not a forecast, promise, or personalized portfolio return.",
)

FINANCIAL_FREEDOM_WITHDRAWAL = VersionedAssumption(
    identifier="financial-freedom-withdrawal-baseline",
    value=Decimal("0.0350"),
    version="2026-10-02",
    effective_from=date(2026, 10, 2),
    reviewed_at=date(2026, 10, 2),
    review_by=date(2026, 12, 31),
    source_url="https://www.pfrda.org.in/documents/33652/198397/Pension%2BSecurity%2Bin%2BIndia-Book.pdf",
    methodology="Illustrative 3.5% withdrawal scenario informed by independent research hosted by PFRDA; not an official PFRDA rule, safe guarantee, or personalized recommendation.",
)

FINANCIAL_FREEDOM_ASSUMPTIONS = {
    "annual_inflation_rate": FINANCIAL_FREEDOM_INFLATION,
    "annual_return_rate": FINANCIAL_FREEDOM_RETURN,
    "withdrawal_rate": FINANCIAL_FREEDOM_WITHDRAWAL,
}

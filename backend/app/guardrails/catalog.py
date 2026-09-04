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
    version="2026-08-30",
    effective_from=date(2026, 8, 30),
    reviewed_at=date(2026, 8, 30),
    review_by=date(2026, 9, 30),
    source_url="https://www.rbi.org.in/commonperson/English/Scripts/speeches.aspx?Id=3161",
    methodology="Conservative long-term planning baseline; inflation may differ from the RBI target and actual household inflation.",
)

FINANCIAL_FREEDOM_RETURN = VersionedAssumption(
    identifier="financial-freedom-product-neutral-return-baseline",
    value=Decimal("0.0800"),
    version="2026-08-30",
    effective_from=date(2026, 8, 30),
    reviewed_at=date(2026, 8, 30),
    review_by=date(2026, 9, 30),
    source_url="https://investor.sebi.gov.in/calculators/Assets_Allocations.html",
    methodology="Product-neutral illustration only; it is not a forecast, promise, or personalized portfolio return.",
)

FINANCIAL_FREEDOM_WITHDRAWAL = VersionedAssumption(
    identifier="financial-freedom-withdrawal-baseline",
    value=Decimal("0.0350"),
    version="2026-08-30",
    effective_from=date(2026, 8, 30),
    reviewed_at=date(2026, 8, 30),
    review_by=date(2026, 9, 30),
    source_url="https://www.pfrda.org.in/en/web/pfrda/home",
    methodology="Conservative planning methodology, not a market rate or a recommendation for retirement withdrawals.",
)

FINANCIAL_FREEDOM_ASSUMPTIONS = {
    "annual_inflation_rate": FINANCIAL_FREEDOM_INFLATION,
    "annual_return_rate": FINANCIAL_FREEDOM_RETURN,
    "withdrawal_rate": FINANCIAL_FREEDOM_WITHDRAWAL,
}

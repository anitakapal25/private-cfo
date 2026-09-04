"""Effective-date enforcement for regulatory and financial assumptions."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


class StaleAssumptionError(ValueError):
    pass


@dataclass(frozen=True)
class VersionedAssumption:
    identifier: str
    effective_from: date
    review_by: date
    source_url: str
    value: Decimal | None = None
    version: str | None = None
    reviewed_at: date | None = None
    methodology: str | None = None


def require_current_assumption(
    assumption: VersionedAssumption, as_of: date | None = None
) -> None:
    check_date = as_of or date.today()
    if check_date < assumption.effective_from:
        raise StaleAssumptionError(
            f"Assumption {assumption.identifier} is not effective until {assumption.effective_from.isoformat()}"
        )
    if check_date > assumption.review_by:
        raise StaleAssumptionError(
            f"Assumption {assumption.identifier} expired for review on {assumption.review_by.isoformat()}"
        )

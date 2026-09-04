from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.agent import CalculationRecord
from app.routers.agent_v1 import get_financial_memory_monthly_summary


MONTH = date(2026, 9, 1)


def fact(fact_type: str, value: str, user_id=None, month: date = MONTH):
    timestamp = datetime(2026, 9, 4, tzinfo=timezone.utc)
    return SimpleNamespace(
        fact_id=uuid4(), user_id=user_id or uuid4(), fact_type=fact_type,
        value=Decimal(value), unit="INR", source_type="user_statement",
        source_id=None, verification_status="verified", period_kind="monthly",
        period_start=month, observed_at=timestamp, verified_at=timestamp,
        created_at=timestamp,
    )


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def all(self):
        return self.rows


class FakeDb:
    def __init__(self, rows):
        self.rows = rows
        self.added = []
        self.commits = 0

    def query(self, model):
        return FakeQuery(self.rows)

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commits += 1


@pytest.mark.parametrize("present", [(), ("monthly_income",), ("monthly_expenses",), ("monthly_debt_payments",), ("monthly_income", "monthly_expenses")])
def test_monthly_summary_never_substitutes_zero_for_missing_facts(present):
    user_id = uuid4()
    rows = [fact(kind, "100", user_id) for kind in present]
    db = FakeDb(rows)

    result = get_financial_memory_monthly_summary("2026-09", SimpleNamespace(user_id=user_id), db)

    assert result["status"] == "incomplete"
    assert result["money_left"] is None
    assert set(result["missing"]) == {"monthly_income", "monthly_expenses", "monthly_debt_payments"} - set(present)
    assert db.added == []
    assert db.commits == 0


def test_complete_monthly_summary_persists_traceable_calculation():
    user_id = uuid4()
    rows = [
        fact("monthly_income", "87600", user_id),
        fact("monthly_expenses", "42000", user_id),
        fact("monthly_debt_payments", "10000", user_id),
    ]
    db = FakeDb(rows)

    result = get_financial_memory_monthly_summary("2026-09", SimpleNamespace(user_id=user_id), db)

    assert result["status"] == "complete"
    assert result["money_left"] == {"amount": "35600.00", "currency": "INR"}
    assert result["calculation_id"]
    assert result["assumptions"]["formula"] == "monthly_income - monthly_expenses - monthly_debt_payments"
    assert len(result["provenance"]) == 3
    assert db.commits == 1
    assert len(db.added) == 1
    assert isinstance(db.added[0], CalculationRecord)
    assert db.added[0].user_id == user_id

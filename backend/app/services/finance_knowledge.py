"""Reviewed public education. Runtime lookup has no network or user-data access."""
from datetime import date, datetime, timezone
import hashlib
from typing import Literal
from pydantic import Field
from app.services.conversation_contracts import StrictModel, Topic
from app.guardrails.agent_input import evaluate_agent_input

BOOK = "https://investor.sebi.gov.in/pdf/downloadable-documents/Financial%20Education%20Booklet%20-%20English.pdf"
BUDGET = "https://investor.sebi.gov.in/moneymatters-inc-exp.html"
TAX = "https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/ITR1-FAQ?mobile-app=1"
INSURANCE = "https://policyholder.gov.in/how-to-buy-property-insurance-and-from-whom"
RETIREMENT = "https://www.pfrda.org.in/en/financial-literacy/retirement-planner-scheme"

class KnowledgeEntry(StrictModel):
    topic: Topic
    url: str
    publisher: str
    content: str
    locator: str
    version: str = "education-2026-09-11"
    published_at: str | None = None
    effective_from: date | None = None
    reviewed_at: date = date(2026, 9, 11)
    review_by: date = date(2026, 9, 30)
    status: Literal["reviewed", "pending", "conflicting"] = "reviewed"
    review_basis: str = "Source checked during implementation; general education only; not regulatory approval"
    limitations: list[str] = Field(default_factory=lambda: ["General education; no current product prices, rates, or personalized recommendation"])

CATALOGUE = [
    KnowledgeEntry(topic="budgeting", url=BUDGET, publisher="SEBI", locator="Ways to Manage Income and Expense", content="A budget records income and spending. Separate essential spending from wants, track what you actually spend, and set aside money for your goals."),
    KnowledgeEntry(topic="emergency_fund", url=BUDGET, publisher="SEBI", locator="Build an Emergency Fund", content="An emergency fund is money set aside for unexpected expenses or financial setbacks. Your reserve coverage can be calculated from confirmed accessible assets and monthly expenses."),
    KnowledgeEntry(topic="debt", url=BOOK, publisher="SEBI", published_at="2020-11", locator="Chapter 2: What is Debt?; Chapter 8", content="Debt is borrowed money that must be repaid. Review repayment obligations before borrowing. Artha can show debt balances and payment metrics from confirmed records."),
    KnowledgeEntry(topic="investing", url=BOOK, publisher="SEBI", published_at="2020-11", locator="Chapters 2 and 5", content="Investing puts savings into assets with an expectation of returns and a risk of loss. Diversification spreads exposure; it does not guarantee gains. Compare risk, liquidity, costs, and time horizon."),
    KnowledgeEntry(topic="insurance", url=INSURANCE, publisher="IRDAI Policyholder", locator="How to Buy Insurance and From Whom", content="Insurance promises compensation under specified policy terms when a covered event occurs. Read the coverage, exclusions, claim procedure, and intermediary authorization. Artha compares recorded coverage only against a target you explicitly choose."),
    KnowledgeEntry(topic="retirement", url=RETIREMENT, publisher="PFRDA", locator="Retirement Planner Scheme", content="Retirement planning prepares for financial needs after regular employment income ends. Review needs, risks, costs, liquidity, and progress over time. Artha uses confirmed scenario inputs and reviewed assumptions for projections, which are not guarantees."),
    KnowledgeEntry(topic="tax", url=TAX, publisher="Income Tax Department", locator="FAQs: selecting an ITR form and preparing records", content="Tax return requirements depend on income sources and residential status. Reconcile tax records with supporting documents. Current personalized tax calculations remain unavailable until Artha's tax rule catalogue is reviewed."),
]
APPROVED_URLS = frozenset(entry.url for entry in CATALOGUE)

def lookup_topic(topic: Topic, *, today: date | None = None, catalogue=None) -> dict:
    now = today or datetime.now(timezone.utc).date()
    entries = [entry for entry in (CATALOGUE if catalogue is None else catalogue) if entry.topic == topic]
    if len(entries) != 1 or entries[0].status != "reviewed":
        return {"type": "unsupported_coverage", "code": "SOURCE_UNREVIEWED", "content": "Reviewed information for this topic is unavailable or conflicting."}
    entry = entries[0]
    if entry.reviewed_at > now or entry.review_by < now or (entry.effective_from and entry.effective_from > now):
        return {"type": "unsupported_coverage", "code": "SOURCE_EXPIRED", "content": "This topic needs a source review before I can present it as current."}
    if entry.url not in APPROVED_URLS or not evaluate_agent_input(entry.content).allowed:
        return {"type": "unsupported_coverage", "code": "SOURCE_INVALID", "content": "This source cannot be used safely."}
    return {"type": "sourced_explanation", "content": entry.content,
            "source_id": hashlib.sha256(f"{entry.topic}:{entry.version}".encode()).hexdigest()[:24],
            "topic": entry.topic, "source_url": entry.url, "publisher": entry.publisher,
            "version": entry.version, "reviewed_at": entry.reviewed_at.isoformat(),
            "review_by": entry.review_by.isoformat(), "published_at": entry.published_at,
            "effective_from": entry.effective_from.isoformat() if entry.effective_from else None,
            "locator": entry.locator, "limitations": entry.limitations}

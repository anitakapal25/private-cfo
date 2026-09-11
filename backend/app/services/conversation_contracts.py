"""Provider-independent, read-only conversation contracts. No ownership arguments."""
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

VERSION = "conversation-v1"
Topic = Literal["budgeting", "debt", "emergency_fund", "investing", "insurance", "retirement", "tax"]
ToolName = Literal[
    "calculate_net_worth", "calculate_monthly_surplus", "calculate_debt_metrics",
    "calculate_emergency_fund_coverage", "get_goal_progress", "forecast_cash_flow",
    "calculate_coverage_gap", "calculate_financial_freedom_projection", "lookup_finance_topic",
]

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class ToolArguments(StrictModel):
    period_start: date | None = None
    topic: Topic | None = None

    @field_validator("period_start")
    @classmethod
    def month_start(cls, value):
        if value is not None and value.day != 1:
            raise ValueError("Period must be the first day of a month")
        return value

class ToolRequest(StrictModel):
    name: ToolName
    arguments: ToolArguments = Field(default_factory=ToolArguments)

class Plan(StrictModel):
    calls: list[ToolRequest] = Field(default_factory=list, max_length=8)
    clarification: Literal["topic", "period", "verified_facts"] | None = None
    continue_planning: bool = False

class ConversationState(StrictModel):
    tools: list[ToolName] = Field(default_factory=list, max_length=8)
    period_start: date | None = None
    topic: Topic | None = None
    pending: Literal["topic", "period", "verified_facts"] | None = None
    evidence_references: list[str] = Field(default_factory=list, max_length=8)

class EvidenceSelection(StrictModel):
    # No free-form financial prose: server renders authorized text and values.
    references: list[str] = Field(max_length=8)

class ToolEvidence(StrictModel):
    reference: str
    tool_name: ToolName
    status: Literal["complete", "missing", "unavailable"]
    narrative: str
    blocks: list[dict]

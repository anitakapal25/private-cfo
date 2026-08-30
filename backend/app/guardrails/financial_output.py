"""Validation for outputs produced by deterministic financial tools."""

from typing import Any, Mapping


class FinancialOutputError(ValueError):
    pass


REQUIRED_AUDIT_FIELDS = ("calculation_id", "assumptions", "timestamp")


def validate_financial_output(result: Mapping[str, Any]) -> None:
    """Require traceability metadata before a financial result reaches the agent."""
    if "error" in result:
        return
    missing = [field for field in REQUIRED_AUDIT_FIELDS if not result.get(field)]
    if missing:
        raise FinancialOutputError(
            f"Financial tool output is missing audit metadata: {', '.join(missing)}"
        )


async def execute_financial_tool(tool, input_data: Mapping[str, Any]) -> dict[str, Any]:
    result = await tool.execute(dict(input_data))
    validate_financial_output(result)
    return result


#!/usr/bin/env python3
"""Opt-in synthetic live planner/composition probes; never reads .env or a user DB."""
import argparse
import asyncio
from datetime import date
from decimal import Decimal
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.core.conversation_gateway import OpenAIConversationGateway
from app.services.conversation_contracts import VERSION
from app.services.conversation_tools import HANDLERS

CASES = [
    ("overview", "How am I doing financially?", {}, {"calculate_net_worth", "calculate_monthly_surplus"}),
    ("paraphrase", "How much remains after my expenses?", {}, {"calculate_monthly_surplus"}),
    ("education", "Explain budgeting", {}, {"lookup_finance_topic"}),
    ("follow_up_period", "What about July?", {"tools": ["calculate_monthly_surplus"], "period_start": "2026-08-01"}, {"calculate_monthly_surplus"}),
    ("compound", "Show my net worth and emergency fund coverage", {}, {"calculate_net_worth", "calculate_emergency_fund_coverage"}),
]

def positive_decimal(value):
    result = Decimal(value)
    if not result.is_finite() or result <= 0:
        raise argparse.ArgumentTypeError("Must be a positive finite decimal")
    return result

async def evaluate(args):
    # Conservative reservation per API call: payload <=24k UTF-8 bytes, plus framing.
    per_call = (Decimal(32768) * args.input_price_per_million + Decimal(2400) * args.output_price_per_million) / Decimal(1_000_000)
    gateway = None if args.dry_run else OpenAIConversationGateway(os.environ["ARTHA_EVAL_API_KEY"], args.model)
    reserved, results = Decimal(0), []
    for case_id, question, state, expected in CASES:
        if reserved + per_call > args.max_cost_usd:
            results.append({"case": case_id, "status": "budget_exhausted"})
            continue
        reserved += per_call
        if args.dry_run:
            results.append({"case": case_id, "status": "dry_run"})
            continue
        try:
            plan = await asyncio.wait_for(gateway.plan({"question": question, "state": state, "today": "2026-09-11", "allowed_tools": [*HANDLERS, "lookup_finance_topic"], "evidence": []}), 15)
            passed = expected.issubset({call.name for call in plan.calls})
            if case_id == "follow_up_period":
                passed = passed and any(call.arguments.period_start == date(2026,7,1) for call in plan.calls)
            results.append({"case": case_id, "status": "pass" if passed else "fail"})
        except Exception:
            results.append({"case": case_id, "status": "provider_or_validation_failure"})
    if reserved + per_call <= args.max_cost_usd:
        reserved += per_call
        if args.dry_run:
            results.append({"case": "composition", "status": "dry_run"})
        else:
            try:
                selection = await asyncio.wait_for(gateway.compose({"evidence": [{"reference": "synthetic_evidence", "tool": "calculate_net_worth", "status": "missing", "missing": ["total_assets"]}]}), 15)
                results.append({"case": "composition", "status": "pass" if selection.references == ["synthetic_evidence"] else "fail"})
            except Exception:
                results.append({"case": "composition", "status": "provider_or_validation_failure"})
    else:
        results.append({"case": "composition", "status": "budget_exhausted"})
    report = {"model": args.model, "policy_version": VERSION, "approval_reference": args.approval_reference, "reserved_cost_upper_bound_usd": str(reserved), "cost_basis": "operator-supplied current input/output prices; conservative token reservations", "results": results, "limitations": ["Live planner/composition probes only; full offline and PostgreSQL safety acceptance is separate", "Not a regulatory or production release approval"]}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    return 0 if args.dry_run or all(r["status"] == "pass" for r in results) else 1

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="gpt-6-astra")
    parser.add_argument("--max-cost-usd", type=positive_decimal, required=True)
    parser.add_argument("--input-price-per-million", type=positive_decimal, required=True)
    parser.add_argument("--output-price-per-million", type=positive_decimal, required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.dry_run and not os.environ.get("ARTHA_EVAL_API_KEY"):
        parser.error("Live evaluation requires ARTHA_EVAL_API_KEY; .env is never read")
    return asyncio.run(evaluate(args))
if __name__ == "__main__":
    raise SystemExit(main())

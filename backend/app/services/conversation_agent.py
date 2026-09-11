"""Bounded conversational orchestration with deterministic evidence rendering."""
import asyncio
import calendar
from datetime import date, datetime
import time
from zoneinfo import ZoneInfo
import re
from pydantic import ValidationError
from app.guardrails.agent_input import evaluate_agent_input
from app.guardrails.data_redaction import sanitize_question
from app.guardrails.regulatory_language import evaluate_financial_request, Decision, PRODUCT_SELECTION_RESPONSE
from app.services.agent_orchestrator import AgentAnswer, AgentOrchestrator, Intent
from app.services.conversation_contracts import ConversationState, Plan, ToolRequest, ToolArguments, EvidenceSelection
from app.services.conversation_tools import HANDLERS

OVERVIEW = ["calculate_net_worth", "calculate_monthly_surplus", "calculate_emergency_fund_coverage", "calculate_debt_metrics", "get_goal_progress"]
TOPIC_WORDS = {"budgeting": ("budget", "income", "spending", "cash flow", "saving"), "debt": ("debt", "loan", "emi", "borrow"), "emergency_fund": ("emergency", "reserve"), "investing": ("invest", "fund", "stock", "diversif", "compound", "inflation"), "insurance": ("insurance", "coverage", "policy"), "retirement": ("retire", "pension", "epf", "nps", "freedom"), "tax": ("tax", "itr", "tds")}
TOOL_WORDS = {"calculate_net_worth": ("net worth", "assets", "liabilities"), "calculate_monthly_surplus": ("cash flow", "surplus", "saved", "save", "expenses", "money left"), "calculate_emergency_fund_coverage": ("emergency", "reserve"), "calculate_debt_metrics": ("debt", "loan", "emi"), "get_goal_progress": ("goal",), "forecast_cash_flow": ("forecast",), "calculate_coverage_gap": ("insurance", "coverage"), "calculate_financial_freedom_projection": ("financial freedom", "retire early", "freedom plan")}
CLARIFICATIONS = {"topic": "What would you like to understand: a financial concept or a calculation from your confirmed records?", "period": "Which month and year should I use?", "verified_facts": "Please record or confirm the missing information in Financial Memory, then ask again."}
CURRENT_INFORMATION_TERMS = (
    "current rate", "latest rate", "interest rate", "tax slab", "tax limit",
    "deduction limit", "current price", "market price", "nav", "expense ratio",
    "return today", "today's return", "current rule", "latest rule",
)
CURRENT_INFORMATION_SUBJECTS = (
    "tax", "itr", "epf", "ppf", "nps", "pension", "fund", "stock",
    "share", "bond", "insurance", "rate", "price", "rule", "limit",
)


def requested_period(question, state, today):
    lower = question.lower()
    if "last month" in lower or "previous month" in lower:
        return date(today.year - (today.month == 1), 12 if today.month == 1 else today.month - 1, 1)
    if "this month" in lower:
        return today.replace(day=1)
    iso = re.search(r"\b((?:19|20)\d{2})-(0[1-9]|1[0-2])(?:-01)?\b", lower)
    if iso:
        return date(int(iso[1]), int(iso[2]), 1)
    for month in range(1, 13):
        if re.search(rf"\b(?:{calendar.month_name[month].lower()}|{calendar.month_abbr[month].lower()})\b", lower):
            year = re.search(r"\b(?:19|20)\d{2}\b", lower)
            return date(int(year[0]) if year else state.period_start.year if state.period_start else today.year, month, 1)
    return None


def local_plan(question, state, today):
    lower = question.lower()
    period = requested_period(question, state, today)
    followup = bool(re.match(r"\s*(?:what about|and |same|how about)", lower))
    education = bool(re.match(r"\s*(?:what (?:is|are|does)|explain|define|tell me about|how does|why )", lower)) and not re.search(r"\bmy\b", lower)
    topics = [topic for topic, terms in TOPIC_WORDS.items() if any(t in lower for t in terms)]
    if education:
        return Plan(calls=[ToolRequest(name="lookup_finance_topic", arguments=ToolArguments(topic=t)) for t in topics[:8]], clarification=None if topics else "topic")
    if any(t in lower for t in ("overview", "doing financially", "healthy are my finances", "financial situation")):
        names = OVERVIEW
    else:
        names = [name for name, terms in TOOL_WORDS.items() if any(t in lower for t in terms)]
        if "forecast_cash_flow" in names and "calculate_monthly_surplus" in names:
            names.remove("calculate_monthly_surplus")
    if not names and followup:
        names = state.tools
        if "lookup_finance_topic" in names:
            return Plan(calls=[ToolRequest(name="lookup_finance_topic", arguments=ToolArguments(topic=state.topic))] if state.topic else [], clarification=None if state.topic else "topic")
    if followup and period is None:
        period = state.period_start
    if period and period > today.replace(day=1):
        return Plan(clarification="period")
    return Plan(calls=[ToolRequest(name=name, arguments=ToolArguments(period_start=period)) for name in names[:8]], clarification=None if names else "topic")


def model_evidence(results):
    # Values already exist in authorized evidence, but the planner only needs status.
    return [{"reference": r.reference, "tool": r.tool_name, "status": r.status,
             "missing": [field for b in r.blocks if b["type"] == "missing_data" for field in b.get("fields", [])]} for r in results]

class ConversationAgent:
    def __init__(self, executor, gateway=None, *, max_rounds=2, max_tools=8, timeout=30):
        self.executor, self.gateway = executor, gateway
        self.max_rounds, self.max_tools, self.timeout = min(max_rounds, 2), min(max_tools, 8), min(timeout, 30)
        self.metrics = {"planner_calls": 0, "tool_calls": 0, "fallback": False, "validation_rejections": 0, "source_hits": 0, "tool_failures": 0}

    async def answer(self, question, state=None, *, disconnected=None, today=None):
        started = time.monotonic()
        today = today or datetime.now(ZoneInfo("Asia/Kolkata")).date()
        try:
            state = ConversationState.model_validate(state or {})
        except ValidationError:
            state = ConversationState()
        if not evaluate_agent_input(question).allowed:
            return AgentOrchestrator(None, self.executor.user_id).answer(question), state, False
        boundary = evaluate_financial_request(question)
        public_only = boundary.decision == Decision.BLOCK
        education_question = bool(re.match(r"\s*(?:what (?:is|are|does)|explain|define|how does)", question, re.I)) and not re.search(r"\bmy\b", question, re.I)
        if public_only and boundary.reason != "specific_product_or_guaranteed_outcome" and not education_question:
            return AgentOrchestrator(None, self.executor.user_id).answer(question), ConversationState(), False
        if re.search(r"\b(?:tax|itr|tds)\b", question, re.I) and not re.match(r"\s*(?:what|explain|define|how does)", question, re.I):
            return AgentOrchestrator(None, self.executor.user_id).answer("calculate my tax"), ConversationState(), False
        normalized_question = question.lower()
        asks_for_current_information = (
            any(term in normalized_question for term in CURRENT_INFORMATION_TERMS)
            or (
                any(marker in normalized_question for marker in ("current", "latest", "today"))
                and any(subject in normalized_question for subject in CURRENT_INFORMATION_SUBJECTS)
            )
        )
        if asks_for_current_information:
            answer = AgentAnswer(
                Intent.GENERAL_EDUCATION,
                "I do not have reviewed current information for that rate, price, limit, or rule.",
                [{
                    "type": "unsupported_coverage",
                    "code": "CURRENT_INFORMATION_UNAVAILABLE",
                    "content": (
                        "This request needs a dated official source that is not yet in "
                        "Artha's approved catalogue. I will not answer it from model memory."
                    ),
                }],
            )
            return answer, ConversationState(), False
        if re.search(r"\b(?:document|upload|statement|payslip|salary slip)\b", question, re.I):
            answer = AgentAnswer(Intent.DOCUMENT, "Use Documents in the desktop application to review local files. Only confirmed structured facts can be used here.", [{"type": "unsupported_coverage", "code": "LOCAL_DOCUMENT_ONLY", "content": "Documents and extracted text cannot be processed in chat."}])
            return answer, ConversationState(), False
        if re.search(r"\b(?:create|save|update|delete|confirm|change)\b.{0,30}\b(?:fact|plan|income|expense|record)\b", question, re.I):
            return AgentAnswer(Intent.PLANNING_ACTION, "Use Financial Memory or My Plan to review and confirm changes. Chat cannot change your records.", [{"type": "clarification", "code": "verified_facts", "content": CLARIFICATIONS["verified_facts"]}]), ConversationState(), False
        fallback = local_plan(question, state, today)
        if public_only:
            public_topic = "insurance" if "insurance" in question.lower() else "investing"
            fallback = Plan(calls=[ToolRequest(name="lookup_finance_topic", arguments=ToolArguments(topic=public_topic))])
            state = ConversationState()
        results, seen = [], set()
        plan = fallback
        used = False
        active = self.gateway
        # Periods are resolved from the original locally, before amounts are stripped.
        explicit_period = requested_period(question, state, today)
        context = {"question": sanitize_question(question), "state": {"tools": state.tools, "period_start": state.period_start.isoformat() if state.period_start else None, "topic": state.topic, "pending": state.pending}, "today": today.isoformat(),
                   "requested_period": explicit_period.isoformat() if explicit_period else None,
                   "allowed_tools": ["lookup_finance_topic"] if public_only else [*HANDLERS, "lookup_finance_topic"]}
        async def checkpoint():
            if disconnected and await disconnected():
                raise asyncio.CancelledError()
            if time.monotonic() - started >= self.timeout:
                raise TimeoutError()
        try:
            for _ in range(self.max_rounds):
                await checkpoint()
                if active:
                    try:
                        self.metrics["planner_calls"] += 1
                        plan = Plan.model_validate(await asyncio.wait_for(active.plan({**context, "evidence": model_evidence(results)}), max(0.01, self.timeout - (time.monotonic() - started))))
                        if any(call.name not in context["allowed_tools"] for call in plan.calls):
                            raise ValueError("Tool outside request permissions")
                        for proposed in plan.calls:
                            if proposed.name == "lookup_finance_topic":
                                if proposed.arguments.topic is None or proposed.arguments.period_start is not None:
                                    raise ValueError("Invalid public arguments")
                            elif proposed.arguments.topic is not None:
                                raise ValueError("Invalid financial arguments")
                        used = True
                    except Exception:
                        self.metrics["fallback"] = True
                        active, plan = None, fallback
                for call in plan.calls:
                    await checkpoint()
                    # An explicit user period cannot be overridden by the model.
                    if call.name != "lookup_finance_topic":
                        if explicit_period:
                            call.arguments.period_start = explicit_period
                        elif re.match(r"\s*(?:what about|and |same|how about)", question.lower()) and state.period_start:
                            call.arguments.period_start = state.period_start
                        elif call.arguments.period_start is not None:
                            # The model may not invent a historical period absent local evidence.
                            call.arguments.period_start = None
                        if call.arguments.period_start and call.arguments.period_start > today.replace(day=1):
                            self.metrics["validation_rejections"] += 1
                            plan.clarification = "period"
                            continue
                    key = call.model_dump_json()
                    if key in seen:
                        continue
                    if len(seen) >= self.max_tools:
                        break
                    seen.add(key)
                    self.metrics["tool_calls"] += 1
                    try:
                        # Each call is transactionally isolated: a failed tool does not erase prior evidence.
                        with self.executor.db.begin_nested() if self.executor.db is not None else _NoTransaction():
                            result = self.executor.execute(call, public_only=public_only)
                        results.append(result)
                        self.metrics["source_hits"] += int(call.name == "lookup_finance_topic" and result.status == "complete")
                    except Exception:
                        self.metrics["validation_rejections"] += 1
                        self.metrics["tool_failures"] += 1
                        if hasattr(self.executor, "failures"):
                            self.executor.failures.append(call)
                if not plan.continue_planning or not active or len(seen) >= self.max_tools:
                    break
            await checkpoint()
            if active and results:
                try:
                    draft = EvidenceSelection.model_validate(await asyncio.wait_for(active.compose({"evidence": model_evidence(results)}), max(0.01, self.timeout - (time.monotonic() - started))))
                    refs = [r.reference for r in results]
                    if len(draft.references) != len(refs) or set(draft.references) != set(refs):
                        raise ValueError("Unknown or missing evidence references")
                    by_ref = {r.reference: r for r in results}
                    results = [by_ref[ref] for ref in draft.references]
                except Exception:
                    self.metrics["fallback"] = True
                    self.metrics["validation_rejections"] += 1
        except (TimeoutError, asyncio.CancelledError):
            self.metrics["fallback"] = True
        blocks = [b for r in results for b in r.blocks]
        narrative = "\n\n".join(r.narrative for r in results)
        if public_only and not education_question:
            narrative = PRODUCT_SELECTION_RESPONSE
        pending = "verified_facts" if any(r.status == "missing" for r in results) else plan.clarification
        if pending:
            blocks.append({"type": "clarification", "code": pending, "content": CLARIFICATIONS[pending]})
        if not results:
            narrative = PRODUCT_SELECTION_RESPONSE if public_only else CLARIFICATIONS[pending or "topic"]
            blocks.append({"type": "unsupported_coverage", "code": "NO_VERIFIED_RESULT", "content": "I do not have a verified result for this request. You can ask about confirmed finances or the supported education topics."})
        if any(r.status != "complete" for r in results) or self.metrics["tool_failures"]:
            blocks.append({"type": "unsupported_coverage", "code": "PARTIAL_RESULTS", "content": "Available evidence is shown; some parts could not be completed."})
        tools = list(dict.fromkeys(r.tool_name for r in results))
        period = next((c.arguments.period_start for c, _ in self.executor.calls if c.arguments.period_start), None)
        topic = next((c.arguments.topic for c, _ in self.executor.calls if c.arguments.topic), None)
        new_state = ConversationState(tools=tools, period_start=period, topic=topic, pending=pending, evidence_references=[r.reference for r in results])
        self.metrics["latency_ms"] = int((time.monotonic() - started) * 1000)
        intent = Intent.FINANCIAL_OVERVIEW if len([t for t in tools if t != "lookup_finance_topic"]) > 1 else Intent(HANDLERS[tools[0]].intent) if tools and tools[0] in HANDLERS else Intent.GENERAL_EDUCATION
        return AgentAnswer(intent, narrative, blocks, policy_decision="block" if public_only else "allow"), new_state, used

class _NoTransaction:
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False

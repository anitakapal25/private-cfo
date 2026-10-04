# Engineering Issue Log

**Status:** Active issue record
**Last reviewed:** 2026-10-02
**Owner:** Product and engineering

This file records notable implementation problems, their diagnosis, and the
solution evidence after they are resolved. Keep unresolved observations separate
from verified fixes so this document does not overstate the application's status.

## ENG-001: Conceptual debt question returns a source-review error

**Status:** Code fixed locally; release verification pending
**Observed:** 2026-10-01
**Area:** Conversational finance agent / educational question routing

### User-visible symptom

When a user asks:

> Is total debt and loan balance are different things?

the assistant does not explain the difference. It displays:

- `This topic needs a source review before I can present it as current.`
- `Available evidence is shown; some parts could not be completed.`

### Expected behavior

The assistant should recognize this as a general financial-education comparison
and provide a clear, source-grounded explanation. It should not treat the question
as a request to calculate the user's personal debt metrics.

### Current request workflow

1. The authenticated conversation endpoint receives the question.
2. The conversational agent checks safety and regulatory boundaries.
3. A narrow phrase matcher decides whether the request is an educational question
   eligible for cited web research.
4. The model planner or deterministic fallback selects a validated read-only tool.
5. The selected tool returns evidence, which the server validates and renders.

### Confirmed cause

Two conditions combine to produce the failure:

1. The education-question matcher recognizes forms such as `what is`, `explain`,
   and `how does`, but it does not recognize a comparison phrased as
   `is ... different?`. The deterministic fallback also sees the words `debt` and
   `loan` as calculation keywords, so it can route the question toward personal
   debt metrics instead of concept education.
2. If the model selects the public debt-topic lookup, that catalogue entry is also
   unavailable on the observation date. Its `review_by` date was 2026-09-30, and
   the application correctly fails closed after that date with `SOURCE_EXPIRED`.
   The orchestration layer then adds `PARTIAL_RESULTS` because the evidence was not
   complete.

### Evidence

- `backend/app/services/conversation_agent.py` contains the narrow education
  phrase matcher and the debt/loan calculation keyword routing.
- `backend/app/services/finance_knowledge.py` gives the reviewed education entries
  a `review_by` date of 2026-09-30 and returns `SOURCE_EXPIRED` after that date.
- A focused reproduction using the exact question on 2026-10-01 produced no web
  research call and returned both `SOURCE_EXPIRED` and `PARTIAL_RESULTS`.
- The existing conversation-agent suite passed 46 tests, showing that this wording
  is a missing behavioral case rather than a failure covered by the current tests.

### Impact

Users can receive an unavailable-source message for a simple conceptual question.
The response is technically fail-closed, but it is not useful and makes the
assistant appear unable to answer basic finance questions.

### Resolution approach

Pending. When this issue is fixed, record:

- the routing or classification change;
- the reviewed source/content change, including its review date;
- the regression test covering this exact comparison wording and close paraphrases;
- verification results and any remaining limitations.

Do not resolve this issue by only extending the catalogue expiry date. A source
date must change only after its content and source have actually been reviewed.

On 2026-10-02, the debt education source was reviewed and renewed in commit
`2ba6f3e`. The comparison-question routing remains open; the source review alone
does not prove that this exact wording now receives the right answer.

Later on 2026-10-02, a screenshot showed the same conceptual question returning
personal debt metrics from confirmed facts. The routing was then changed to
recognize `is ... different?` and `how are ... different?` as education requests.
For such requests, the model may call only the public topic lookup, so a proposed
personal calculator call is rejected. The curated debt explanation now distinguishes
one loan's outstanding balance from total borrowing obligations. Offline tests cover
the exact screenshot wording, close paraphrases, a model proposing the wrong tool,
and personal debt requests that should still calculate. The conversation-agent
suite passed (58 tests). Live browser and deployment verification remain pending.

On 2026-10-03, a synthetic local API check confirmed that the comparison question
uses public education research rather than a personal debt calculation. The
frontend now renders the resulting explanation as readable paragraphs, bullets,
and compact source links; browser tests cover this presentation. Deployment
verification remains pending.

### Interview explanation

I investigated a case where a basic debt question returned a compliance-style
source error. I traced the request through the API, intent routing, model/tool
selection, evidence validation, and UI blocks. The problem was an interaction
between a narrow intent matcher and an intentionally expired source catalogue.
The safety control behaved correctly, but the routing caused it to activate for
the wrong user intent. The fix makes concept detection explicit and limits the
available tools before model planning, while preserving personal calculations
when the user actually asks for them.

## ENG-002: Financial-freedom question asks vaguely for missing information

**Status:** Code fixed and pushed; release verification pending
**Observed:** 2026-10-02
**Area:** Conversational planning, assumption freshness, and follow-up UI
**Commit:** `2ba6f3e`

### User-visible symptom

For “How can I achieve financial freedom in 10 years?”, the assistant told the user
to record or confirm unspecified information in Financial Memory and ask again.
It also displayed “I do not have a verified result.” When the user supplied the
projection inputs, the server instead reported that planning assumptions had
expired. The message did not distinguish missing personal values from an expired
application assumption.

### Expected behavior

The assistant should request the five personal inputs needed for the projection:
current age, target age, current monthly living expenses, existing savings and
investments set aside for the goal, and planned monthly contribution. It should
present the result only through the deterministic calculator. If an application
assumption is stale, the projection should fail closed and explain that the user
does not need to enter more financial information to fix it.

### Diagnosis and change

The model planner could return a generic clarification without invoking the
recognized calculator, so the server never received the calculator's precise
missing-field response. The UI also made the follow-up awkward. The conversation
path now invokes the recognized read-only calculator to discover missing fields,
preserves its follow-up wording, and offers direct entry of relevant values. The
projection form keeps entered values when an assumption is stale.

The three planning scenario inputs had a 2026-09-30 review-by date. Their values
were retained after a documented source and methodology review, versioned
2026-10-02, and given a 2026-12-31 next-review date. This was a review of
illustrative inputs, not a claim that their outcomes are guaranteed. The FY
2023–24 tax calculator and unverified insurance education source remain blocked.
See `docs/assumption-review-2026-10-02.md` for the source-level record.

### Evidence and remaining work

- The focused backend tests passed (58 tests), including missing-field and
  assumption-freshness cases. Documentation checks passed.
- The local API was restarted against synthetic Postgres and reported ready;
  the frontend responded locally. A real-browser end-to-end projection check
  after the restart has not been recorded.
- Full backend verification still had four failures and eleven errors in the
  Windows environment. The repository freshness check still fails on the
  intentionally expired FY 2023–24 tax rule; the guardrail check reports a
  local `.env` file. Frontend type-check and lint could not run in the
  restricted shell because Node could not access the workspace path.
- Financial-model and engineering release approvals and deployment evidence
  remain outstanding. A Git push is not evidence of a successful deployment.

Further local regression checks on 2026-10-04 covered the newly confirmed-facts
follow-up: after a net-worth request names missing fields, "I have added both
fields now answer" retries the pending calculator and clears the stale
clarification. The financial-freedom response now explains the scenario with
everyday costs and tool-sourced figures. Focused backend tests passed (94), and
frontend type-check and build passed. The full backend suite still reports four
failures and eleven errors in the Windows test environment; the expired historical
tax rule and local `.env` guardrail findings remain open.

### Interview explanation

The difficult part was making the assistant useful without letting it guess.
I traced one failed question across model planning, deterministic tools,
assumption checks, and the UI. I let the calculator name the missing values,
then made the assistant ask for those values directly. I reviewed the expired
planning assumptions against their sources while leaving rules that still need
substantive work blocked. The trade-off was a more useful answer that still
preserves the system's trust boundary.

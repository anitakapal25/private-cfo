# Assumption and education source review — 2026-10-02

**Status:** Local implementation review; release approval pending  
**Last reviewed:** 2026-10-02

This is an implementation review for local testing, not release approval. No tax rule or calculation formula was renewed by changing its date. Financial-model owner and engineering approval remain required before deployment under `workflows/calculation-release.md`.

## Financial-freedom scenario inputs

The three values in `backend/app/guardrails/catalog.py` are unchanged. Their source, methodology, version, and review window were reviewed on 2026-10-02; next review is due 2026-12-31. They are illustrative inputs, not forecasts or advice. Historical results retain their original version and should not be silently recalculated.

| Input | Value | Evidence and interpretation |
| --- | ---: | --- |
| Inflation | 6% | [Government Gazette, 2026–31 inflation target](https://egazette.gov.in/WriteReadData/2026/271285.pdf): 6% is the upper tolerance bound, used here as a conservative scenario. It is not a forecast of household inflation. |
| Annual return | 8% | [SEBI asset allocation calculator](https://investor.sebi.gov.in/calculators/Assets_Allocations.html) allows an expected return as a user input; SEBI does not endorse this particular number. 8% remains an internal product-neutral illustration. |
| Withdrawal | 3.5% | [Research hosted by PFRDA, *Pension Security in India*](https://www.pfrda.org.in/documents/33652/198397/Pension%2BSecurity%2Bin%2BIndia-Book.pdf), chapter “Balancing Acts: Safe Withdrawal Rates in the Indian Context,” discusses 3–3.5%. The authors' analysis is not an official PFRDA rule or guarantee. |

## Public education

General budgeting and emergency-fund material was checked against [SEBI income and expense guidance](https://investor.sebi.gov.in/moneymatters-inc-exp.html); debt against [SEBI borrowing guidance](https://investor.sebi.gov.in/moneymatters-borrowmoney.html); investing against [SEBI pre-investment guidance](https://investor.sebi.gov.in/investment-thingsbeforeinv.html); retirement against the [PFRDA retirement planner](https://www.pfrda.org.in/en/financial-literacy/retirement-planner-scheme); and general tax concepts against the [Income Tax Department ITR FAQ](https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/ITR1-FAQ?mobile-app=1). These six topics were reviewed on 2026-10-02, with next review due 2026-12-31. This review does not authorize personalized advice, current product claims, or tax calculations.

## Still blocked

- The FY 2023–24 tax rule entry expired on 2024-03-31. The tax calculator still implements that year's rules; a current-year legal and calculation update, independently checked examples, and release approval are needed. Its freshness check must continue to fail.
- The IRDAI insurance education page could not be verified during this review, so that topic retains its 2026-09-30 expiry and remains unavailable until the source and wording are reviewed.

Before release, the owner and engineering reviewer should inspect these sources and methodology, run the calculation and regression checks, record approval, and assess historical-output presentation. An earlier source change or contradiction requires review before the stated next-review date.

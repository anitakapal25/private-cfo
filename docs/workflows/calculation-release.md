# Financial Calculation Release Workflow

**Status:** Required for every calculation or assumption change  
**Last reviewed:** 2026-08-30  
**Owner:** Financial-model owner and engineering reviewer

1. Define units, timing, rounding, effective dates and authoritative sources.
2. Record a versioned assumption with a mandatory review-by date.
3. Implement the formula outside presentation and LLM code.
4. Add golden examples, boundary cases, invariants and property-based tests where useful.
5. Compare results with an independent implementation or qualified reviewer.
6. Persist calculation version, inputs, assumptions, source version and timestamp.
7. Run backward-impact analysis for existing users.
8. Obtain financial-model and engineering approval before deployment.
9. Monitor result distributions and retain rollback capability.

Expired assumptions must fail closed; warnings alone are insufficient for tax or
regulatory calculations presented as current.

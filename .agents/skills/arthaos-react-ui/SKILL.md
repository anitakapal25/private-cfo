---
name: arthaos-react-ui
description: Design or implement Private CFO React pages, presentation-layer API integration, accessibility, responsiveness, and visual behavior; not backend financial logic or broad evidence-based audits.
---

# ArthaOS React UI

Inspect existing components and styles first. Reuse dependencies and primitives; do not duplicate Button, Card, Input, Badge, or Modal components. Keep pages compositional, reusable primitives in `components/ui`, and domain components in `features/<feature>`.

The UI must not calculate financial values or supply ownership identity. Surface API provenance, freshness, assumptions, and confidence when relevant. Handle loading, empty, error, success, unauthorized, stale-assumption, low-confidence, and guardrail-refusal states.

Preserve semantic HTML, accessible names, keyboard behavior, and responsive navigation. Run frontend type-check, lint, and build. Claim visual verification only after inspecting the page in a real browser.

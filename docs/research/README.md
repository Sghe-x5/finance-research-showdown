# Research documentation index

This directory separates current decisions from frozen milestones and historical
working material. When two files disagree, use the highest item in the relevant
section below rather than the newest-looking filename.

## Current pre-reveal state

| Document | Role |
|---|---|
| [`DAY3_FINAL_PRE_REVEAL.md`](DAY3_FINAL_PRE_REVEAL.md) | Machine-phase boundary, extended reporting calendar, power count, bottleneck, and expansion estimate |
| [`FIELD_LINEAGE_AND_MANAGER_AUDIT.md`](FIELD_LINEAGE_AND_MANAGER_AUDIT.md) | Official SEC field lineage, repaired join/parser findings, manager overlap, and fallback audit |
| [`BLIND_BENCHMARK_READINESS.md`](BLIND_BENCHMARK_READINESS.md) | Canonical decision that v3—not v2—is the facility file for clean reviewers |
| [`REVIEWER_GUIDE.md`](REVIEWER_GUIDE.md) | Operational handoff for independent reviewers |
| [`PREREGISTRATION_V3_DRAFT.md`](PREREGISTRATION_V3_DRAFT.md) | Draft measurement guard only; it is not an approved preregistration or freeze authorization |

## Frozen milestone record

| Document | Status |
|---|---|
| [`01_DAY1_CANONICAL_FINDINGS.md`](01_DAY1_CANONICAL_FINDINGS.md) | Canonical Day 1 reconciliation |
| [`02_PROJECT_DECISIONS.md`](02_PROJECT_DECISIONS.md) | Reconciled project decisions |
| [`03_PREREGISTRATION_V2.md`](03_PREREGISTRATION_V2.md) | Frozen Day 2 preregistration |
| [`04_DAY2_EXECUTION_PLAN.md`](04_DAY2_EXECUTION_PLAN.md) | Day 2 execution plan |
| [`DAY2_RESULTS.md`](DAY2_RESULTS.md) | Day 2 exploratory result and caveats |
| [`05_DAY2_EXTERNAL_AUDIT.md`](05_DAY2_EXTERNAL_AUDIT.md) | External audit that motivated Day 3 measurement repair |
| [`DAY3_MEASUREMENT_REPAIR.md`](DAY3_MEASUREMENT_REPAIR.md) | Day 3 repair log and boundaries |

Day 1 and Day 2 are also frozen in Git tags:

- `showdown-day1-reconciled-2026-08-12`
- `showdown-day2-mechanism-2026-08-13`

## Supporting and operational documents

- `DAY2_RESEARCH_MEMO.md` and `README_DAY2.md` explain the supplied Day 2 pack.
- `CODEX_DAY2_PROMPT.md`, `06_CODEX_PUSH_PROMPT.md`, and
  `07_GIT_COMMIT_PLAN.md` are execution provenance, not current research claims.
- `history/` contains the original Claude snapshot. It is useful for audit and
  interviews, but it is explicitly non-canonical.

## Interpretation rules

- Never treat a planning-power count as predictive evidence.
- Never treat the Day 2 adjusted error as confirmatory; its advantage was driven
  by one borrower and the original matching benchmark was circular.
- Do not reveal target-current outcomes before a final preregistration and sample
  freeze are approved.
- Do not use superseded blind files for additional clean reviewers.
- Keep private keys, raw archives, API responses, and credentials outside Git.

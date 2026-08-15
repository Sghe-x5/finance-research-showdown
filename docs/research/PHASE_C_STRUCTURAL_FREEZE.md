# Phase C Structural Consensus Freeze

## Freeze boundary

This commit freezes the independent Phase C structural consensus before any numeric outcome reveal. It preserves all 37 Phase B observation IDs and changes no Phase A label, Phase C label, sample row, preregistered rule, formula, threshold, or evaluator byte.

The frozen consensus is [`data/day4/day4_structural_mapping_consensus.csv`](../../data/day4/day4_structural_mapping_consensus.csv), SHA-256:

`a64a484f32f79f0053e06f15f2c0557e4198535a163fd29cb2a35fc73d91b768`

## Independent-review audit

- Structural Reviewer D input SHA-256: `4e1e9de7716eb98f37d453fbeb350716495773099d26057c78fca887fb9e2726`.
- Structural Reviewer E input SHA-256: `4f83b2164c6abb0eabc616ae663188d260a903971cd8e06d08136f16c048f595`.
- Agreement on all three decision fields: **37/37**.
- Adjudication required: **no**.
- Frozen IDs equal the Phase B included-sample IDs exactly.
- All non-review structural fields equal the blind structural packet exactly.
- Rows replaced or removed: **0**.

Structural labels:

| Field | Counts |
|---|---|
| `target_current_same_facility` | yes 35; no 1; uncertain 1 |
| `target_current_aggregation_valid` | yes 36; uncertain 1 |
| `position_status` | continuing 35; unmatched_disappearance 2 |

## Structural-stage power guard

- Continuing observations: **35**.
- Continuing source-event clusters: **32**.
- Unique continuing borrowers: **18**.
- Cluster guard: 32 ≥ 25 — passed.
- Borrower guard: 18 ≥ 15 — passed.

The two unmatched-disappearance observations remain in the frozen denominator and are not replaced.

## Frozen dependencies

- Phase B sample freeze commit: `d27dec28cc361db03680820997b2d9e7e7463cda`.
- Included-sample SHA-256: `011da2ab9ccc39f5c2530295fee1b555377f4a2b36a302e45183873af603a670`.
- Final preregistration SHA-256: `6b19ee878c103122ae1734bfbd480aec2fdd88ae35b6368f24655a26b552fcdc`.
- Evaluator SHA-256: `bcea297f43603316d4d3bc5fef9762bc2749eaddf36a3253222af66e8f132615`.

The machine-readable freeze record is [`data/day4/structural_mapping_freeze.json`](../../data/day4/structural_mapping_freeze.json).

## What is not in this commit

This commit contains no valuation marks, principal, cost, fair value, FV/principal ratio, prediction, error, return, numeric outcome file, result, or reveal authorization. Phase D may begin only after this structural-freeze commit exists and is pushed.

# Day 5 ShadowNAV replication preregistration

Status: **FINAL — STRICT/SUPPORTING samples frozen; Phase C/D not authorized**

Date: 2026-08-15

Starting feasibility commit: `2be1c2bab16705b4090012c6eed0d8d8bc6782a9`

This final document preserves the outcome-blind Day 5 replication hierarchy, formulas, statistical procedures, decision rules, and review boundaries after Phase A human consensus and Phase B sample freeze. No Day 5 target-current structure or numerical outcome had been opened at this freeze. Human review removed candidates only through the locked rules; it did not add, replace, reclassify, or move candidates between pre-review layers.

## 1. Two-layer replication hierarchy

### Primary replication layer: STRICT NEW-BORROWER

The outcome-blind pre-review maximum is 34 observations, 34 source-event clusters, and 19 unique normalized borrowers. A candidate belongs to STRICT only when all of the following were established before human review:

- its borrower is absent from all Day 2 and Day 3 development or inspected fixtures;
- its borrower is absent from the Day 4 confirmatory sample;
- its source event is absent from Day 4;
- the source-target relationship is cross-manager;
- target timing is verified under the Day 4 cutoff definition;
- target listed-equity status is verified; and
- canonical manager/adviser mapping is verified.

**Only STRICT determines the Day 5 primary replication status.**

### Secondary layer: SUPPORTING NEW-FUND

The outcome-blind pre-review maximum is 75 observations, 75 source-event clusters, and 39 borrowers. At least one fund is outside the frozen Day 4 19-fund universe; previously seen borrowers may remain. Day 4 source events remain excluded and the layer is cross-manager only.

The supporting output is always labelled `secondary_supporting`. It cannot convert a STRICT `exploratory_inconclusive`, `underpowered_inconclusive`, or `data_quality_inconclusive` result into `pass`; it cannot alter the primary formulas, thresholds, sample, or status. Its borrower overlap with Day 4 and with development borrowers is reported as structural metadata, never used as an outcome-dependent filter.

The verified V2 candidate sets are nested: STRICT is a subset of SUPPORTING. The single blind packet therefore contains all 75 supporting-candidate rows without exposing either layer flag. Layer membership is frozen at candidate construction in a private, Git-ignored mapping.

## 2. Frozen mechanism and predictions

No formula or threshold changes from frozen Day 4.

Movement is defined on an aggregated `economic_facility_v2` as:

```text
abs(source_current_mark - source_prior_mark) >= 0.005
```

The persistence baseline is:

```text
prediction_B0 = target_prior_mark
```

ShadowNAV is:

```text
prediction_SN =
    target_prior_mark
    + (source_current_mark - source_prior_mark)
```

The independent event is one unique source economic-facility movement event. When one source event has multiple targets, target-observation error differences are averaged inside `source_event_cluster_id` before the primary test.

No clipping, winsorization, shrinkage, weighting, machine learning, optimized threshold, optimized reporting-window filter, or post-outcome universe change is allowed. The Day 4 observation that windows longer than five days appeared stronger remains secondary only and is not a selection rule.

## 3. Position status and missingness

After a later, separately frozen structural review, each frozen row must have exactly one status:

- `continuing`;
- `partial_repayment`;
- `full_repayment`;
- `sale_exit`;
- `refinancing_amendment`;
- `unmatched_disappearance`; or
- `uncertain`.

The mark test uses only human-confirmed `continuing` rows. Every excluded, uncertain, missing, repaid, exited, or disappeared row remains in the denominator and attrition report and is never replaced.

If any human-confirmed `continuing` row lacks `target_prior_mark`, `source_prior_mark`, `source_current_mark`, or `target_current_mark`, that layer is `data_quality_inconclusive`; no value is imputed and the primary result cannot be `pass`.

## 4. Primary STRICT power guard and allowed statuses

After event review and later structural review, STRICT is `underpowered_inconclusive` if it contains either:

- fewer than 25 independent continuing source-event clusters; or
- fewer than 15 unique continuing borrowers.

Supporting-only rows can never be promoted into STRICT, and excluded or uncertain STRICT rows cannot be replaced. The only allowed primary statuses are:

- `pass`;
- `exploratory_inconclusive`;
- `underpowered_inconclusive`; and
- `data_quality_inconclusive`.

## 5. Six simultaneous primary PASS criteria

Subject to the data-quality and power guards, STRICT passes only if all six frozen Day 4 criteria hold simultaneously:

1. Cluster-level `MAE_SN < MAE_B0`.
2. Relative MAE improvement is at least 10%: `(MAE_B0 - MAE_SN) / MAE_B0 >= 0.10`.
3. The borrower-clustered one-sided sign-flip permutation test gives `p < 0.05`.
4. The borrower-cluster bootstrap 95% interval for `MAE_SN - MAE_B0` lies entirely below zero.
5. The full-sample mean error difference is below zero and every leave-one-borrower-out mean difference remains below zero.
6. The mean source-event-cluster error difference is negative in a strict majority of represented untouched periods.

If the power and data-quality guards pass but only some criteria hold, STRICT is `exploratory_inconclusive`.

## 6. Frozen statistical procedures

- The primary estimand is the event-weighted mean of source-event-cluster paired absolute-error differences, `absolute_error_SN - absolute_error_B0`.
- Each source-event cluster contributes the arithmetic mean of its target-observation error differences.
- Cluster-level MAE for each method is the arithmetic mean of its within-cluster target-observation absolute errors.
- Dependence is handled by a borrower-clustered one-sided sign-flip permutation test. Each draw assigns one shared sign to all source-event clusters of one normalized borrower.
- The permutation test uses 100,000 draws, seed `20260814`, and add-one correction `(extreme + 1) / (draws + 1)`.
- The borrower-cluster bootstrap resamples borrowers with replacement and retains all their source-event clusters. It uses 10,000 draws, seed `20260814`, and the percentile 2.5%–97.5% interval.
- Leave-one-borrower-out passes only when the full-sample mean difference and every leave-one-borrower-out mean difference are below zero.
- Period direction passes only when more than half of represented untouched periods have a negative mean source-event-cluster difference.

The SUPPORTING layer is evaluated after authorized reveal with the same formulas and procedures. It reports MAE B0, MAE ShadowNAV, relative improvement, borrower-clustered permutation p, borrower-bootstrap interval, leave-one-borrower-out, period direction, and six criterion booleans, but receives only the label `secondary_supporting` and cannot change primary status.

## 7. Outcome-blind event review

Two new clean reviewers, Day 5 Event Reviewer F and Reviewer G, independently receive only `data/day5/day5_event_review_blind.csv` and `docs/research/DAY5_EVENT_REVIEW_PROTOCOL.md`. They do not receive layer membership, Day 4 results, one another's answers, private mappings, target-current data, valuation numbers, GitHub, SEC, or web access.

They label:

1. `source_temporal_same_facility`;
2. `source_to_target_prior_same_facility`;
3. `source_aggregation_valid`;
4. `target_prior_aggregation_valid`.

Mechanical inclusion is `yes` only when all four checks are `yes`; `no` when at least one is `no`; and `uncertain` when none is `no` and at least one is `uncertain`. Disagreements require explicit adjudication by a separate adjudicator without outcome access. No majority vote is allowed.

Review may remove candidates only through these locked rules. It may never add a row outside V2, replace a failed row, move a supporting-only row into STRICT, or alter pre-review membership.

## 8. Staged reveal status

- **Phase A completed:** outcome-blind event-review consensus was frozen in Commit A `88f358cbfcc0783ca54b9d8329b2d3a393702819`.
- **Phase B completed:** the STRICT and SUPPORTING included samples are frozen with this final preregistration in the same Git commit. The commit containing these files is the required `sample_freeze_commit` in any later authorization record.
- **Phase C not yet authorized in this document:** only a separate later commit may materialize target-current non-valuation structure for exactly the frozen SUPPORTING IDs and send it to clean structural reviewers.
- **Phase D prohibited:** numeric outcomes may be opened only after structural consensus is separately frozen and a complete authorization record verifies every bound hash and commit.

The evaluator must verify its own SHA-256, the byte-frozen Day 4 statistical dependency, all bound file hashes and freeze commits, exact frozen-ID equality, STRICT subset membership, and equality between numeric-file structural labels and separately frozen structural consensus. Numeric outcomes cannot redefine structure.

## 9. Final Phase A/B frozen record

- Phase A consensus SHA-256: `aef9a7d0e5fc89ef9e6d019f0ea0f1f09495089fcad74590e4747b4e27c2902b`.
- Phase A commit: `88f358cbfcc0783ca54b9d8329b2d3a393702819`.
- STRICT included sample: 31 observations, 31 source-event clusters, 16 borrowers; SHA-256 `a42c462a83d960ed241fc48d91b89035a7cd0be44aeca0dcac5d20453b5719dd`.
- SUPPORTING included sample: 67 observations, 67 source-event clusters, 33 borrowers; SHA-256 `d4890bcbce1f8880cb56ca9ffe86071d3514064d4ff8488c685ef5f3cb62b50f`.
- Frozen evaluator SHA-256: `ecc92fb08bbf18781b88a24ba44a2d2c152eb9ac2d8d62d582606b5091f73ac4`.
- Membership-key SHA-256: `6c8e142d9ff70af3bcee32a40fbbbb68ee459276d2a2ec449219123d61201733`; the key remains Git-ignored and is not published.
- Sample-generation code SHA-256: `a69dcdbad3ce25e83e7307a1f7ec33bb25604d4d2ec3d549f3dfb9373852ae86`.
- Duplicate-vote audit SHA-256: `7ccff4d8a11e856a85ad230aadca00e1f0dce377d427153e07898fc778fae2ce`; status `pass_no_duplicate_independent_vote`.

The pre-structural STRICT sample remains above both planning guards: at least 25 clusters and at least 15 borrowers. These are not final continuing counts; the unchanged guard is applied again after Phase C structural review.

## 10. Current prohibitions

- No target-current numeric reveal.
- No Day 5 prediction, error, MAE, effect size, p-value, bootstrap interval, or PASS/FAIL calculation.
- No result tag.
- No row replacement, supporting-to-STRICT promotion, outcome-dependent membership change, or threshold change.

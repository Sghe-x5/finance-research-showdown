# Preregistration V3 — Confirmatory ShadowNAV Draft V2

**Status: DRAFT — NO FREEZE OR REVEAL AUTHORIZED.**

This document incorporates the pre-Phase-B dependence and duplicate-vote corrections requested after the outcome-blind human event review. It does not freeze a sample, authorize access to target-current facilities, or authorize a target-outcome reveal. No result may be calculated from target same-quarter marks until this draft is independently approved and the separate Phase B and Phase C freezes are completed.

The final Phase A consensus SHA-256 is `2a0c763e423b5616b3f9093f54a0073d5e8577b0fe4f5769fb2ca60ff26f9591`. It contains 37 included observations in 34 source-event clusters; three uncertain observations/clusters remain excluded and retained in the audit trail. These counts are outcome-blind and do not constitute a Phase B freeze.

## 1. Matcher interpretation

- The literal point-estimate precision gate passed: **58/60 = 96.7%**.
- A strict statistical guarantee that precision is at least 95% was not established: the exact one-sided 95% lower bound is **89.9%**.
- The matcher is permitted for confirmatory research only with human review of every included movement event.
- Autonomous production precision of at least 95% is not claimed.
- The cross-manager benchmark was **11/11 confirmed**, but the sample is small.
- Same-manager observations are not part of the primary ShadowNAV hypothesis.
- The alias benchmark metric is named **resolved_candidate_alias_yield** in documentation. Its value remains 18/89 = **20.2%**.

Recall is conditional on the generated candidate universe and is not population recall.

## 2. Universe

- Current 19-fund universe.
- Cross-manager observations only.
- Exact normalized borrower blocking only.
- No borrower-alias expansion.
- No same-manager observations.
- No 2025Q3 observations; that period remains development-contaminated.
- Only human-confirmed exact economic facilities may enter the confirmatory sample.
- The 11 previously seen development borrowers remain excluded in every period.
- The matcher, `economic_facility_v2`, reporting order, and movement threshold are locked inputs and may not be changed for this test.

## 3. Independent unit

The primary independent unit is a **unique source economic-facility movement event**.

If one source event is linked to multiple targets, paired error differences are first averaged within the `source_event_cluster_id`. One source shock therefore receives one independent vote, regardless of the number of eligible targets.

The human review packet contains one row per source-target observation. Inclusion is permitted only when all four measurement checks are `yes`:

1. `source_temporal_same_facility`;
2. `source_to_target_prior_same_facility`;
3. `source_aggregation_valid`;
4. `target_prior_aggregation_valid`.

`include_for_confirmatory_test=yes` is invalid unless all four checks are `yes`. Missing, failed, or uncertain rows are retained in the review record and are not replaced.

Before Phase B, a duplicate economic-vote guard must join the included review IDs to stable pre-reveal economic facility IDs. The duplicate identity contains report period, normalized borrower, source ticker, target ticker, source-prior economic facility ID, and target-prior economic facility ID. If two included observations have the same duplicate identity but different `source_event_cluster_id` values, the process stops with `duplicate_independent_vote_blocker`. No row may be selected, merged, promoted, or replaced automatically after human review.

The current outcome-blind audit checked all 37 proposed included observations and found no duplicate identity and no independent-vote blocker. The two uncertain Dealer Tire suffix rows remain excluded; they were not promoted or replaced.

## 4. Movement

```text
abs(source_current_mark - source_prior_mark) >= 0.005
```

The threshold was formulated after Day 2 and is tested only on untouched periods 2024Q1–2025Q2. Movement is measured only on an aggregated `economic_facility_v2`, never on an individual XBRL slice.

## 5. Locked prediction formulas

### B0 persistence

```text
prediction_B0 = target_prior_mark
```

### ShadowNAV source-delta transfer

```text
prediction_SN =
target_prior_mark
+ (source_current_mark - source_prior_mark)
```

There is no clipping, winsorization, entry-price adjustment, or post-freeze formula change.

## 6. Primary outcome

For continuing target facilities:

```text
absolute_error_SN - absolute_error_B0
```

A negative value means that ShadowNAV improved on persistence. Target-observation differences are averaged inside each source-event cluster before the primary test.

## 7. Position disappearance and attrition

Position disappearance is not silently excluded. Before reveal, every frozen row must use exactly one of these categories:

- `continuing`;
- `partial_repayment`;
- `full_repayment`;
- `sale_exit`;
- `refinancing_amendment`;
- `unmatched_disappearance`;
- `uncertain`.

The primary mark test is calculated only for `continuing` facilities. The full persistence/attrition flow is published for all frozen rows. Failed, missing, ambiguous, and disappeared observations remain in the denominator and are never replaced.

If any human-confirmed `continuing` row lacks `target_prior_mark`, `source_prior_mark`, `source_current_mark`, or `target_current_mark`, the overall result status is **`data_quality_inconclusive`**. Such a row remains in the attrition and missingness reports, is not imputed or replaced, and the result cannot be `PASS`.

The final result is **`underpowered_inconclusive`** regardless of point estimates if either of these thresholds fails after structural review:

- fewer than **25 independent continuing source-event clusters**; or
- fewer than **15 unique continuing borrowers**.

Both thresholds are fixed before target-current structure or numeric outcomes are opened and may not be changed after Phase B.

## 8. Primary success criteria

ShadowNAV passes the mechanism gate only if all six conditions hold simultaneously:

1. Cluster-level `MAE_SN < MAE_B0`.
2. Relative MAE improvement is at least 10%: `(MAE_B0 - MAE_SN) / MAE_B0 >= 0.10`.
3. The borrower-clustered one-sided sign-flip permutation test gives `p < 0.05`.
4. The borrower-cluster bootstrap 95% interval for `MAE_SN - MAE_B0` does not cross zero and lies below zero.
5. Leave-one-borrower-out analysis does not show that all benefit is produced by one borrower.
6. The direction of the effect is negative in a strict majority of untouched periods represented in the continuing sample.

If only some conditions hold, the result is **exploratory/inconclusive**, not `PASS`.

## 9. Statistical procedures fixed before reveal

- Observation absolute errors are calculated only after reveal authorization.
- Each source-event cluster contributes the arithmetic mean of its target-observation error differences.
- Cluster-level MAE for each method is the arithmetic mean of the corresponding within-cluster target-observation absolute errors.
- The primary estimand remains the event-weighted mean of source-event-cluster paired error differences.
- The **borrower-clustered one-sided sign-flip permutation test** groups source-event clusters by normalized borrower. Each draw generates one random sign per unique borrower and applies that same sign to every source-event-cluster difference from that borrower. The signed statistic is the event-weighted mean across all source-event clusters; two events from one borrower are never flipped independently. The alternative is that the mean paired error difference is below zero. The test uses 100,000 deterministic Monte Carlo draws, seed `20260814`, and the add-one correction `(extreme + 1) / (draws + 1)`.
- The borrower-cluster bootstrap resamples borrowers with replacement, retains all source-event clusters belonging to each sampled borrower, uses 10,000 draws and seed `20260814`, and reports the percentile 2.5%–97.5% interval.
- Leave-one-borrower-out is a separate robustness check. It is secondary to and does not replace the 15-borrower power guard, the borrower-clustered permutation test, or the borrower-cluster bootstrap. It passes the dominance check only if the full-sample mean difference is below zero and every leave-one-borrower-out mean difference remains below zero.
- Period direction passes only when more than half of represented untouched periods have a negative mean source-event-cluster difference.

No statistical parameter may be tuned after outcomes are opened.

## 10. Secondary outputs

- Target-observation MAE.
- Median absolute error.
- Fraction of observations improved.
- Results by untouched period.
- Results by source.
- Results by target.
- Reporting-window strata fixed as `<=2 days`, `>2 and <=5 days`, and `>5 days`.
- Leave-one-source-out.
- Leave-one-target-out.
- Persistence/disappearance outcomes for all frozen rows.

These outputs are secondary and cannot override a failed primary mechanism gate.

## 11. Prohibitions

- No stock returns.
- No NAV aggregation.
- No machine learning.
- No parameter tuning.
- No universe expansion.
- No alias-expanded events.
- No same-manager primary observations.
- No 2025Q3.
- No target-current structural access before Phase C authorization.
- No numeric target-current or source-mark access before Phase D authorization.
- No changes to formulas, sample rules, evaluator, or tests after freeze.

## 12. Mandatory staged review and reveal

### Phase A — event measurement review

Two independent clean reviewers label the sanitized 40-row review packet. They have no navigable filing links, marks, private outcome data, or evidence-key mapping. Disagreements are adjudicated without access to marks or private outcome data. No majority vote substitutes for explicit adjudication.

Only rows with final consensus `yes` on all four measurement checks may have `include_for_confirmatory_test=yes` and enter the proposed sample. Failed and uncertain rows remain recorded and are not replaced.

Phase A is complete but not frozen as a confirmatory sample by this draft. The final consensus has 37 included observations, 34 included source-event clusters, and three uncertain observations/clusters retained outside the proposed sample. Human labels and inclusion decisions are unchanged by the pre-Phase-B correction.

### Phase B — confirmatory sample freeze

A separate commit must freeze all of the following before any target-current data is available:

- final included `review_observation_id` values;
- included `source_event_cluster_id` values;
- human event-review consensus SHA-256;
- preregistration SHA-256;
- evaluator SHA-256;
- sample-generation code SHA-256;
- included observation count;
- included source-event cluster count;
- unique included borrower count;
- borrower-to-cluster-count distribution;
- maximum source-event clusters contributed by one borrower;
- SHA-256 of `data/day4/confirmatory_borrower_cluster_distribution.csv`;
- SHA-256 and passing status of `data/day4/confirmatory_duplicate_vote_audit.json`.

The borrower counts must be derived from final consensus, not hardcoded. The freeze record must contain no target-current structural or numeric data. A passing duplicate-vote audit is necessary but does not itself authorize or create Phase B. The Phase B freeze must be a separate later commit before Phase C begins.

### Phase C — structural outcome reveal

After Phase B, reveal only non-numeric target-current structure:

- borrower/facility identifier;
- facility type;
- lien;
- currency;
- reference rate;
- spread;
- maturity;
- funded status;
- constituent descriptions;
- aggregation lot count.

Phase C must not reveal principal, cost, fair value, FV/principal, any mark, prediction, error, or return.

Phase C uses two new clean reviewers who did not perform Phase A. Their recorded roles are **Structural Reviewer D** and **Structural Reviewer E**; a separate adjudicator resolves disagreements. Each reviewer works in a completely new isolated chat.

Structural Reviewers D and E receive only the sanitized target-current structural packet and the structural-review protocol. They must not receive Phase A reviewer labels or notes, adjudication reasons, event-review consensus, include/exclude decisions, source movement size, numeric marks, predictions, or outcomes. The Phase C packet must contain no Phase A review, consensus, reviewer, or adjudication columns.

Two independent reviewers label:

- `target_current_same_facility`: `yes` / `no` / `uncertain`;
- `target_current_aggregation_valid`: `yes` / `no` / `uncertain`;
- `position_status`: `continuing` / `partial_repayment` / `full_repayment` / `sale_exit` / `refinancing_amendment` / `unmatched_disappearance` / `uncertain`;
- `structural_notes`.

Disagreements are adjudicated without numeric marks. The final structural consensus is frozen in a separate commit with its SHA-256. Rows classified `uncertain` remain reported and are not replaced.

### Phase D — numeric reveal

Only after the Phase C structural-mapping consensus freeze may numeric target-current marks, source marks, and prediction errors be materialized.

The evaluator must refuse to open the numeric file unless authorization supplies and verifies:

- `event_review_consensus_sha256`;
- `included_sample_sha256`;
- `sample_freeze_commit`;
- `structural_mapping_consensus_sha256`;
- `structural_mapping_freeze_commit`;
- `preregistration_sha256`;
- `evaluator_sha256`;
- `revealed_outcomes_sha256`;
- `reveal_authorized = true`.

The evaluator independently hashes its own source file, the frozen included-sample file, and the revealed-outcome file. Revealed outcome IDs must equal the frozen included observation IDs exactly: no missing, duplicate, replacement, or extra ID is accepted.

## 13. Freeze boundary

The evaluator is prepared and tested only on synthetic data. Its SHA-256 is recorded separately. The outcome-blind review packet and final Phase A consensus are not a frozen confirmatory sample.

The next authorized action is independent approval of this Draft V2. No Phase B sample freeze, Phase C structural reveal, Phase D numeric reveal, results calculation, or results tag is authorized by this document or by the pre-Phase-B audit outputs.

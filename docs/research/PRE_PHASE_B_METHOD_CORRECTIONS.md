# ShadowNAV Pre-Phase-B Method Corrections

## Status and protected boundary

This is an outcome-blind methodological correction, not a sample freeze or a result. No target-current structure, numeric mark, prediction, error, or outcome was opened. Phase B, Phase C, Phase D, and any results tag remain unauthorized.

The final Phase A consensus SHA-256 supplied by the human review process is:

`2a0c763e423b5616b3f9093f54a0073d5e8577b0fe4f5769fb2ca60ff26f9591`

The final decisions were reconstructed without changing labels by combining the 16 rows resolved in the partial consensus with the 24 separately adjudicated disagreement rows. The result independently derives:

- 37 included observations;
- 34 included source-event clusters;
- 20 unique included borrowers;
- three uncertain observations/clusters excluded and retained in the audit trail;
- zero `include=no` observations.

## Borrower-cluster distribution

The outcome-blind distribution is stored in [`data/day4/confirmatory_borrower_cluster_distribution.csv`](../../data/day4/confirmatory_borrower_cluster_distribution.csv). It contains one row per normalized borrower and no mark or target-current field.

| Included source-event clusters per borrower | Borrowers |
|---:|---:|
| 1 | 13 |
| 2 | 3 |
| 3 | 2 |
| 4 | 1 |
| 5 | 1 |

The maximum contribution is five source-event clusters from one borrower. At a future Phase B freeze, the exact borrower-to-cluster distribution, its SHA-256, the unique-borrower count, and the maximum cluster contribution must be recorded.

## Power guards

The final result is `underpowered_inconclusive` if either post-structural continuing-sample threshold fails:

- minimum 25 independent continuing source-event clusters;
- minimum 15 unique continuing borrowers.

The current pre-structural counts of 34 clusters and 20 borrowers do not guarantee that either continuing threshold will pass after Phase C. The thresholds are fixed now and cannot be relaxed after target-current structure or numeric outcomes are opened.

## Borrower-clustered permutation

The primary estimand remains the event-weighted mean of source-event-cluster paired error differences. The corrected primary randomization procedure is the **borrower-clustered one-sided sign-flip permutation test**:

1. Group source-event clusters by normalized borrower.
2. Draw one random sign for each unique borrower.
3. Apply that sign to every source-event-cluster difference from the borrower.
4. Calculate the event-weighted mean across all signed source-event clusters.
5. Test the alternative that the mean paired error difference is below zero.
6. Use 100,000 deterministic draws, seed `20260814`, and the add-one correction.

Repeated events from one borrower are never flipped independently. The borrower-cluster bootstrap remains the primary interval procedure. Leave-one-borrower-out remains a required robustness check but does not replace the permutation, bootstrap, or 15-borrower power guard.

## Duplicate economic-vote guard

The audit in [`data/day4/confirmatory_duplicate_vote_audit.json`](../../data/day4/confirmatory_duplicate_vote_audit.json) joins review IDs to stable pre-reveal economic facility IDs. Its identity is:

```text
report period
+ normalized borrower
+ source ticker
+ target ticker
+ source-prior economic facility ID
+ target-prior economic facility ID
```

All 37 included rows were checked. No duplicate identity and no cross-cluster duplicate independent vote were found, so the current status is `pass_no_duplicate_independent_vote`. If a future regeneration finds the same identity under different source-event clusters, it must stop with `duplicate_independent_vote_blocker`; it may not choose, merge, promote, or replace a row automatically.

The two uncertain Dealer Tire suffix rows remain excluded, and all three uncertain observations remain in the audit trail.

## Phase C reviewer isolation

Phase C requires two new clean reviewers who did not perform Phase A:

- Structural Reviewer D;
- Structural Reviewer E;
- a separate adjudicator for disagreements.

Each reviewer must work in a completely new isolated chat. They receive only the sanitized target-current structural packet and the structural-review protocol. They do not receive Phase A labels, Phase A notes, adjudication reasons, consensus decisions, inclusion status, source movement size, numeric marks, predictions, or outcomes. The Phase C packet contains no Phase A review fields.

## What this commit does not do

- It does not finalize the preregistration.
- It does not create the Phase B sample freeze.
- It does not reveal target-current structure.
- It does not reveal numeric outcomes or calculate results.
- It does not create a results tag.

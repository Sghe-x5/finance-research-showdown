# Current State — 2026-08-14

## Flagship status

### ShadowNAV — active provisional flagship

Core mechanism:

1. BDC A publicly reports a current-quarter mark for an economic private-credit facility.
2. Listed BDC B holds the same facility but has not yet disclosed its current-quarter result.
3. Use the source mark change, not merely the mark level, to nowcast B's still-unreported mark.
4. Aggregate later to NAV/NII only if facility-level nowcasting works.
5. Test equity returns only after the accounting mechanism works.

Locked conceptual predictor:

```text
B0 persistence:
target_prior_mark

ShadowNAV source-delta transfer:
target_prior_mark + (source_current_mark - source_prior_mark)
```

### Japan Language Wall — demoted under current constraints

The event index remains valuable, but historical documents/numeric forecast revisions were
not recoverable at scale under the current free-access, regional, and licensing constraints.
The retained asset is a prospective live event-normalization product.

## What has been established

- Official SEC BDC flat files exist and are usable.
- Multi-day reporting windows exist.
- Exact facility matching is feasible with human review.
- Matcher point precision is 96.7% on 60 hidden high-confidence positives.
- The exact 95% lower confidence bound does not clear 95%.
- All 37 untouched source-movement events in the current planning set are cross-manager.
- The Day 4 packet has 40 observations / 37 source-event clusters and no explicit numeric marks.

## What has not been established

- ShadowNAV improves target marks out of sample.
- The effect is statistically significant.
- The effect survives leave-one-borrower-out.
- NAV nowcasts improve.
- Any equity alpha exists after costs.
- The current matcher is safe for autonomous production.
- A scalable free historical Japanese numeric-data path exists.

## Immediate blocker

The Day 4 human review packet contains direct filing URLs/provenance that can expose protected
target-current outcomes. It must be sanitized before clean reviewers see it.

A two-stage reveal must be implemented:

1. structural non-numeric target-current reveal and freeze;
2. numeric reveal only after structural consensus is frozen.

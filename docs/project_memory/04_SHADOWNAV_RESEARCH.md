# ShadowNAV Research Memo

## Plain-language idea

Use the first public current-quarter mark from one private-credit holder to infer the
still-unreported mark and later NAV impact at a listed BDC holding the same economic facility.

## Economic mechanism

Private loans are often held by multiple BDCs. They share an underlying borrower/facility
but disclose quarterly marks asynchronously. The source filing can become public days before
the target's own results.

A potentially informative source event is not “a loan is below par.” It is:

```text
source current mark - source prior mark
```

transferred onto the target's own prior valuation level.

## Why this is better than generic earnings prediction

- Same underlying asset.
- Same quarter-end.
- Different publication times.
- Direct later accounting ground truth.
- Free official SEC data.
- LLM/entity-resolution need is concrete.
- Null result still leaves a useful private-credit risk platform.

## Novelty boundary

Commercial platforms already:
- normalize BDC holdings;
- map co-investors;
- compare marks across holders;
- track PIK/non-accrual.

The possible novelty is **not** “we found the same loan.”

The research chain is:

```text
first current-quarter facility disclosure
→ later holder's unreported same-quarter facility mark
→ later portfolio/NAV impact
→ only later, possible equity signal
```

Safe novelty wording:

> We found no published study testing the complete first-reporter
> facility-mark → later-holder mark → Shadow NAV chain.

This does not imply that no private desk uses a similar workflow.

## Key methodological lessons

### Exact borrower is not exact facility

A borrower may have:
- first and second lien;
- revolver, term loan, delayed draw;
- funded and unfunded pieces;
- separate currencies;
- different maturities and spreads;
- debt and equity;
- multiple acquisition lots.

### Entry pricing matters

A below-par level may reflect acquisition basis. Mark changes and cost/par context are more
informative than a raw mark level.

### Same-manager versus cross-manager

Same-manager pairs can share valuation policy, information, committees, and appraisers.
The primary economic hypothesis is cross-manager only.

### Source and target timestamps differ

- Source information time: when the exact facility mark became public.
- Target cutoff: earliest public results/NAV disclosure.
- An earnings release may move the target cutoff without making the source facility mark public.

## Current measurement result

- 60 hidden high-confidence facility matches.
- 58 human-confirmed same facility.
- 2 definite false positives.
- Point precision: 96.7%.
- One-sided exact 95% lower bound: 89.9%.
- Cross-manager: 11/11 in that benchmark.

Interpretation:
- sufficient for confirmatory research with human review of every event;
- insufficient for a production claim of guaranteed ≥95% precision.

## Current confirmatory design

Primary unit:
- unique source economic-facility movement event.

Movement:
```text
abs(source_current_mark - source_prior_mark) >= 0.005
```

Baseline:
```text
target_prior_mark
```

Signal:
```text
target_prior_mark + source_delta
```

Planned pass conditions:
- cluster MAE improvement;
- at least 10% relative MAE improvement;
- one-sided paired permutation p < 0.05;
- borrower-cluster bootstrap interval below zero;
- leave-one-borrower-out direction robustness;
- majority of represented periods in the same direction;
- at least 25 continuing independent clusters, otherwise underpowered/inconclusive.

## What would remain after a null

- open reproducible BDC facility graph;
- economic-facility aggregation benchmark;
- borrower/facility resolution system;
- mark-change and attrition dataset;
- analyst-ready private-credit risk alerts;
- transparent negative finding about first-reporter propagation.

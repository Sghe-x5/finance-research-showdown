# Methods, Preregistration, and Guards

## Data availability

Information time is the earliest timestamp when the required information was public.

- Source facility signal: exact facility mark-public time.
- Target cutoff: first public results/NAV disclosure.
- Period end is never information time.

## Units

- Raw XBRL rows are not observations.
- Economic facility aggregation precedes matching and event construction.
- Primary statistical unit: unique source economic-facility movement event.
- Multiple target observations from one source event are averaged before the primary test.

## Development contamination

Development-only:
- 2025Q3;
- PetVet;
- MRI Software;
- Anaplan;
- Viant Medical;
- Hyland Software;
- Fortis Solutions;
- PPV Intermediate;
- Ping Identity;
- Pye-Barker;
- Auctane;
- Medallia.

They are excluded from confirmatory periods and retained only as fixtures/development evidence.

## Matching

- Exact normalized borrower in primary test.
- No alias expansion in confirmatory sample.
- Cross-manager only.
- Every included movement event receives human measurement review.
- Production precision ≥95% is not claimed.

## Primary formula

```text
B0 = target_prior_mark

SN = target_prior_mark
     + (source_current_mark - source_prior_mark)
```

No clipping, winsorization, or tuning after freeze.

## Planned primary test

Outcome on continuing facilities:

```text
abs_error_SN - abs_error_B0
```

A negative value favors ShadowNAV.

Required success conditions:
1. cluster MAE improves;
2. relative improvement ≥10%;
3. one-sided paired permutation p <0.05;
4. borrower-cluster bootstrap interval below zero;
5. leave-one-borrower-out stays negative;
6. strict majority of periods negative;
7. at least 25 continuing independent clusters, otherwise underpowered/inconclusive.

## Reveal protocol

### Phase A — outcome-blind event review
Review source temporal identity, source-target-prior identity, and aggregation validity.

### Phase B — sample freeze
Freeze included IDs, clusters, human consensus hash, preregistration hash, evaluator hash.

### Phase C — structural target-current reveal
Reveal non-numeric structure only. Independently classify same facility, aggregation, and
position status. Freeze structural consensus.

### Phase D — numeric reveal
Reveal marks and run the fixed evaluator.

## Prohibitions before numeric reveal

- no target current mark;
- no target principal/cost/fair value;
- no target-error metrics;
- no stock return test;
- no NAV aggregation;
- no ML;
- no universe expansion;
- no alias events;
- no formula edits.

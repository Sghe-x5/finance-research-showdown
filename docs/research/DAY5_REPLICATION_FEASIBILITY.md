# Day 5 ShadowNAV replication feasibility

## Scope and boundary

This is an outcome-blind planning screen, not a replication result. Day 4 remains frozen as
`exploratory_inconclusive`; this document does not reinterpret that result. The screen never joins a
target's same-period numeric facility fields, does not materialize target marks or fair values, and
does not calculate either prediction, an error, an effect size, or a significance statistic. No Day 5
sample is frozen here.

The Day 4 mechanism is carried forward unchanged:

- a source movement is `abs(source_current_mark - source_prior_mark) >= 0.005`;
- B0 is the target's prior mark;
- ShadowNAV adds the source's current-minus-prior change to the target's prior mark;
- the independent unit is a unique source economic-facility movement event;
- multiple targets for one source event are averaged inside the source-event cluster;
- inference remains borrower-clustered using the locked Day 4 seeds and draw counts;
- all six Day 4 decision criteria remain unchanged;
- the previously observed longer-window pattern remains secondary and is not a selection filter.

## Inputs and construction

The screen reuses the eight cached official SEC BDC archives and `economic_facility_v2` without
changing either aggregation or matcher rules. It covers 2024Q1 through 2025Q2. The cached 2025Q3
period is excluded as development-contaminated, and the cache contains no later untouched quarter.

For a candidate observation, the program uses only:

1. a source current facility and its uniquely matched source prior facility;
2. the locked 0.5 percentage-point source-movement flag;
3. a uniquely matched target-prior facility for the exact normalized borrower;
4. the source facility's public filing timestamp;
5. a target reporting cutoff.

There is no target-current facility join. For an original Day 4 fund, the reporting cutoff can use the
verified Day 3 reporting order. For a newly screened target, only its periodic filing acceptance is
currently available. That later timestamp is a planning proxy and must be replaced by a verified
earliest results/NAV cutoff before any sample freeze. All selected candidates in this screen use that
proxy, so the counts below are maxima pending calendar review, not a ready sample.

The SEC ticker file is also only a screen for whether a new CIK may be a listed target. Some issuers
have listed debt symbols; equity-target eligibility therefore requires verification before freezing.
The original 19 funds retain their official manager map. New funds use deterministic filer-name family
proxies solely to remove obvious same-manager relationships; their canonical advisers also require
verification.

## Universe definitions

The strict new-borrower universe requires a new source fund and excludes every borrower seen in the
Day 2/Day 3 development work, all globally excluded development aliases, every Day 4 sample
borrower, and every Day 4 source-event ID. Only provisional cross-manager relationships remain.

The new-fund universe requires at least one fund outside the Day 4 19-fund universe. It permits a
borrower seen previously, but still excludes a repeated Day 4 source event and obvious same-manager
relationships. It is supporting feasibility only.

## Fund screen

| Measure | Count |
|---|---:|
| Day 4 funds | 19 |
| Additional CIKs with at least two standard quarter periods | 143 |
| Additional CIKs with an SEC ticker proxy | 37 |
| Additional funds reaching any post-match candidate relationship | 24 |
| Additional funds in strict selected relationships | 15 |
| Additional funds in supporting new-fund relationships | 16 |

## Strict new-borrower feasibility

| Measure | Count |
|---|---:|
| Target observations | 36 |
| Independent source-event clusters | 34 |
| Unique normalized borrowers | 18 |
| Source-target fund pairs | 16 |
| New source funds | 10 |
| New target funds | 9 |
| Exact-borrower target relations considered | 1,548 |
| Rows surviving unique strict facility matching and timing | 36 |
| Rows requiring human facility review | 36 |

Counts by period are 5 in 2024Q1, 5 in 2024Q2, 6 in 2024Q3, 12 in 2024Q4,
6 in 2025Q1, and 2 in 2025Q2. Reporting-window days have p25 2.3573, median 6.0549,
and p75 12.8753. Before applying the primary cross-manager filter, the strict structural
screen contains 1,497 same-manager-proxy rows and 36 cross-manager-proxy rows.

## Supporting new-fund feasibility

| Measure | Count |
|---|---:|
| Target observations | 65 |
| Independent source-event clusters | 63 |
| Unique normalized borrowers | 36 |
| Source-target fund pairs | 25 |
| New source funds | 11 |
| New target funds | 11 |
| Exact-borrower target relations considered | 2,434 |
| Rows surviving unique strict facility matching and timing | 65 |
| Rows requiring human facility review | 65 |

Counts by period are 11 in 2024Q1, 7 in 2024Q2, 10 in 2024Q3, 17 in 2024Q4,
8 in 2025Q1, and 12 in 2025Q2. Reporting-window days have p25 1.9799, median 6.0826,
and p75 10.7910. Before the cross-manager filter, this screen contains 1,944
same-manager-proxy rows and 65 cross-manager-proxy rows.

## Independence and leakage audits

- Duplicate vote identities: 0.
- Duplicate rows: 0.
- Day 4 borrower rows in the full diagnostic candidate set: 98; in strict: 0.
- Day 4 source-event rows in the full diagnostic set: 15; in either selected universe: 0.
- Development-borrower rows in the full diagnostic set: 56; in strict: 0.
- 2025Q3 observations in the output: 0.
- Target same-period numeric rows joined: 0.
- New target outcomes, predictions, errors, effect sizes, and significance statistics calculated: 0.

## Planning conclusion

The preferred planning target of at least 50 borrowers and 80 independent source-event clusters does
not appear feasible in the current strict universe: the pre-review maximum is 18 borrowers and 34
clusters. The broader supporting universe reaches 36 borrowers and 63 clusters, still below both
targets. These maxima can only decline after human facility review, manager verification, listed-equity
verification, and replacement of periodic-filing cutoff proxies with true earliest results cutoffs.

Accordingly, this commit authorizes no sample freeze and no outcome reveal. It records the maximum
clean feasibility currently visible without altering the locked hypothesis or looking at replication
outcomes.

# Day 5 ShadowNAV replication feasibility V2

## Boundary

This is an outcome-blind feasibility expansion. No Day 5 sample is frozen and no
target same-period numeric value, prediction, error, or inferential result is materialized.
The Day 4 hypothesis, economic_facility_v2 aggregation, matcher, and six decision
criteria remain unchanged.

## Official archive expansion

The official SEC monthly BDC archives 2026_01 through 2026_06 were inventoried
and cached outside Git. June has no financial SOI table, consistent with the SEC note.
The locked pipeline recovered 2025-12-31 and 2026-03-31 facility contexts.

## Period independence

2025Q4 is excluded as a replication outcome period because Auctane and Medallia
target outcomes from that period were inspected as quarantined Day 2 calculation
fixtures. It is used only as prior-quarter context for 2026Q1. The 2026Q1 period
passes the pre-outcome independence checks and is included.

## Verified clean maxima

| Universe | Observations | Source-event clusters | Borrowers | Additional funds | Fund pairs |
|---|---:|---:|---:|---:|---:|
| Strict new-borrower | 34 | 34 | 19 | 15 | 15 |
| Supporting new-fund | 75 | 75 | 39 | 21 | 29 |

### Quarter contributions

Strict: `{"2024Q1": 5, "2024Q2": 5, "2024Q3": 5, "2024Q4": 10, "2025Q1": 5, "2025Q2": 2, "2026Q1": 2}`.

Supporting: `{"2024Q1": 11, "2024Q2": 7, "2024Q3": 16, "2024Q4": 18, "2025Q1": 8, "2025Q2": 12, "2026Q1": 3}`.

## Verification and attrition

- Same-manager rows excluded from the primary layer: 2114.
- Target rows excluded for unverified listed-equity status: 129.
- Timing-proxy rows excluded after verification: 136.
- Rows newly enabled by a verified cutoff: 280.
- Common candidate cutoff timestamps changed: 1924.
- Duplicate vote identities: 0.

## Planning decision

The planning target of at least 50 borrowers and 80 independent source-event clusters does not appear achievable in the verified clean maximum.

No sample freeze, outcome reveal, replication decision, or results tag is authorized by this report.

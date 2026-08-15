# Day 5 Phase C structural consensus freeze

Status: **FROZEN — outcome-blind structural mapping; numeric reveal not part of this commit**

The final Reviewer I / Reviewer J consensus and the outcome-blind Adjudicator K decisions are frozen byte-for-byte. The consensus contains 67 unique SUPPORTING observations in the exact frozen order. The 31 STRICT IDs remain the unchanged Phase B subset. No row was added, replaced, or moved between layers, and no human label was modified.

## Integrity

- consensus SHA-256: `44cacbe1fd93b030a51e1e4a9bac270c746a0baef6558372fab384221a50365e`
- supplied audit SHA-256: `9419d0039a689d7ff8a4847f099ff72232bc1d69222c345d71751a003909c77f`
- Phase B sample-freeze commit: `f7ee622aa256dd4ba136dc8de2b477076d8a0229`
- independent agreement: 64 rows
- outcome-blind adjudication: 3 rows

## Frozen structural attrition

- SUPPORTING: 67 observations; 47 continuing clusters and 24 continuing borrowers; statuses `{"continuing": 47, "refinancing_amendment": 1, "uncertain": 2, "unmatched_disappearance": 17}`.
- STRICT: 31 observations; 14 continuing clusters and 10 continuing borrowers; statuses `{"continuing": 14, "uncertain": 1, "unmatched_disappearance": 16}`.
- The STRICT primary status is therefore already bounded to `underpowered_inconclusive` by the unchanged 25-cluster / 15-borrower guards. Supporting evidence cannot override it.

## Boundary

This freeze contains no principal, cost, fair value, FV/principal, mark, prediction, error, effect size, MAE, p-value, or bootstrap result. Numeric reveal may begin only after this freeze exists as its own Git commit and the later authorization binds that full commit SHA.

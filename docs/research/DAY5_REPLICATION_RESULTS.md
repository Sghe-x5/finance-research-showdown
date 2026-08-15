# Day 5 ShadowNAV replication results

Status: **data_quality_inconclusive**

The top-level status is determined only by the frozen STRICT new-borrower layer. It remains `underpowered_inconclusive` unless a stricter data-quality condition applies. The SUPPORTING new-fund layer is descriptive secondary evidence and cannot alter that status. No threshold, formula, layer membership, or human label was changed after freeze.

### Primary STRICT

- final primary status: `data_quality_inconclusive`
- attrition: `{"continuing": 14, "full_repayment": 0, "partial_repayment": 0, "refinancing_amendment": 0, "sale_exit": 0, "uncertain": 1, "unmatched_disappearance": 16}`
- structurally continuing observations/clusters/borrowers: 14 / 14 / 10
- continuing rows with complete marks: 12
- continuing rows missing required marks: 2
- complete-mark continuing clusters: 12
- primary test run: `False`
- power guard: `not evaluated after data-quality stop`
- cluster MAE B0: not calculated (frozen missing-mark rule)
- cluster MAE ShadowNAV: not calculated (frozen missing-mark rule)
- mean paired error difference: not calculated (frozen missing-mark rule)
- relative MAE improvement: not calculated (frozen missing-mark rule)
- borrower-clustered permutation p: not calculated (frozen missing-mark rule)
- borrower bootstrap 95%: not calculated (frozen missing-mark rule)
- leave-one-borrower-out: not calculated (frozen missing-mark rule)
- period direction: not calculated (frozen missing-mark rule)
- six criteria: not evaluated
- all six criteria true: `not evaluated`

The STRICT layer had already failed the frozen power guards because it has 14 continuing clusters (<25) and 10 continuing borrowers (<15). The two missing continuing marks trigger the stricter `data_quality_inconclusive` rule before any primary statistic is calculated.

### Secondary SUPPORTING

- label: `secondary_supporting`
- cannot modify primary status: `true`
- attrition: `{"continuing": 47, "full_repayment": 0, "partial_repayment": 0, "refinancing_amendment": 1, "sale_exit": 0, "uncertain": 2, "unmatched_disappearance": 17}`
- structurally continuing observations/clusters/borrowers: 47 / 47 / 24
- continuing rows with complete marks: 45
- continuing rows missing required marks: 2
- complete-mark continuing clusters: 45
- primary test run: `False`
- power guard: `not evaluated after data-quality stop`
- cluster MAE B0: not calculated (frozen missing-mark rule)
- cluster MAE ShadowNAV: not calculated (frozen missing-mark rule)
- mean paired error difference: not calculated (frozen missing-mark rule)
- relative MAE improvement: not calculated (frozen missing-mark rule)
- borrower-clustered permutation p: not calculated (frozen missing-mark rule)
- borrower bootstrap 95%: not calculated (frozen missing-mark rule)
- leave-one-borrower-out: not calculated (frozen missing-mark rule)
- period direction: not calculated (frozen missing-mark rule)
- six criteria: not evaluated
- all six criteria true: `not evaluated`

### Frozen Day 4 comparison — descriptive only

- Day 4 status: `exploratory_inconclusive`
- cluster MAE B0: 0.06034552795156249
- cluster MAE ShadowNAV: 0.029043301182812512
- relative improvement: 0.5187165947719493
- borrower-clustered permutation p: 0.14939850601493984
- borrower bootstrap 95%: `{"lower": -0.07246575393431369, "upper": 0.0023193058053174094}`

Day 4 and Day 5 are not pooled. The comparison changes no decision rule.

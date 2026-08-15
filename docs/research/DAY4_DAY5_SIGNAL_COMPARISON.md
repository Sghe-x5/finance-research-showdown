# Day 4 versus Day 5 ShadowNAV signal comparison

Status: **DESCRIPTIVE POST-REVEAL COMPARISON — SAMPLES ARE NOT POOLED**

| Sample | Clusters | Borrowers | MAE B0 | MAE ShadowNAV | Relative improvement | Paired difference | Permutation p | Bootstrap 95% CI | Negative periods |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| Day 4 confirmatory | 32 | 18 | 0.0603455 | 0.0290433 | +51.9% | −0.0313022 | 0.149399 | [−0.072466, +0.002319] | 4/6 |
| Day 5 STRICT complete-case exploratory | 12 | 8 | 0.0152940 | 0.0343962 | −124.9% | +0.0191022 | 0.979980 | [+0.004623, +0.039976] | 0/5 |
| Day 5 SUPPORTING complete-case exploratory | 45 | 22 | 0.0103838 | 0.0158768 | −52.9% | +0.0054930 | 0.932841 | [−0.001156, +0.013416] | 1/7 |

Negative paired differences favor ShadowNAV; positive values favor B0 persistence.

## Mechanical questions

**A. Is MAE ShadowNAV below MAE B0 in Day 5 SUPPORTING complete cases?** No. It is 0.01588 versus 0.01038.

**B. Is the paired difference negative?** No. It is +0.005493.

**C. Is the direction consistent with Day 4?** No. Day 4 favored ShadowNAV; both Day 5 layers favor persistence.

**D. Does leave-one-borrower-out remain negative?** No. Every SUPPORTING leave-one-borrower-out estimate is positive, ranging from +0.003687 to +0.007657. Every STRICT estimate is also positive.

**E. Is the effect spread across periods or dominated by one period?** The Day 5 disadvantage is spread across periods: six of seven SUPPORTING periods have a positive paired difference. The largest absolute period contributor is 2024Q1 at 32.6%, and removing it still leaves a positive mean difference.

**F. Is the effect dominated by one borrower?** No. The largest borrower contributes 15.2% of absolute borrower-group contribution, and all borrower leave-one-out estimates remain positive.

**G. Is the effect dominated by one source/target fund pair?** No. The largest pair, CSWC→WHF, contributes 18.3%; every fund-pair leave-one-out mean remains positive.

The Day 5 complete-case reversal is therefore broader than a single-observation artifact. It does not make Day 5 confirmatory—the official status remains `data_quality_inconclusive`—but it is adverse evidence for the proposed unshrunk transfer mechanism.

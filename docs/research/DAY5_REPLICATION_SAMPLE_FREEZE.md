# Day 5 two-layer replication sample freeze

Status: **Phase B frozen outcome-blind; Phase C/D not yet authorized**

Commit A `88f358cbfcc0783ca54b9d8329b2d3a393702819` froze the 75-row human consensus before layer membership was opened. The verified private membership key remained Git-ignored and was then applied without changing any human label or pre-review layer.

## Frozen samples

- STRICT: 31 observations, 31 source-event clusters, 16 borrowers; SHA-256 `a42c462a83d960ed241fc48d91b89035a7cd0be44aeca0dcac5d20453b5719dd`.
- SUPPORTING: 67 observations, 67 source-event clusters, 33 borrowers; SHA-256 `d4890bcbce1f8880cb56ca9ffe86071d3514064d4ff8488c685ef5f3cb62b50f`.
- Final preregistration SHA-256: `909b4068e335cedbe1c819ed47c0e35ffbd6f0ebc9b8bd89ad8f99365a39f1fb`.
- Evaluator SHA-256: `ecc92fb08bbf18781b88a24ba44a2d2c152eb9ac2d8d62d582606b5091f73ac4`.
- Sample-generation code SHA-256: `a69dcdbad3ce25e83e7307a1f7ec33bb25604d4d2ec3d549f3dfb9373852ae86`.
- Membership-key SHA-256: `6c8e142d9ff70af3bcee32a40fbbbb68ee459276d2a2ec449219123d61201733` (key not committed).
- Duplicate-vote audit SHA-256: `7ccff4d8a11e856a85ad230aadca00e1f0dce377d427153e07898fc778fae2ce`; no blocker.

STRICT remains a subset of SUPPORTING. The locked human rule excluded all `no` and `uncertain` rows without replacement. No supporting-only row was promoted into STRICT. The pre-structural STRICT sample has 31 clusters and 16 borrowers, so it is not already guaranteed underpowered; the unchanged 25-cluster/15-borrower guard is applied again after structural review.

No target-current structure or valuation value was opened in this commit. No prediction, error, MAE, p-value, bootstrap interval, result status, or tag was created.

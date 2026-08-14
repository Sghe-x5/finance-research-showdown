# Current Open Questions and Next Steps

## Immediate next action

Apply the Day 4 sanitation/two-stage-reveal patch:

1. Create `confirmatory_event_review_blind_v2.csv`.
2. Remove all navigable filing URLs/accessions/provenance.
3. Preserve exactly 40 observation IDs and 37 cluster IDs.
4. Replace evidence links with opaque hashes.
5. Update preregistration with structural reveal.
6. Harden evaluator authorization and missing-mark failure behavior.

## Then

1. Two clean reviewers independently label the sanitized 40-row packet.
2. Adjudicate disagreements without outcomes.
3. Count included independent clusters.
4. Finalize preregistration.
5. Freeze sample and hashes.
6. Structural non-numeric target-current reveal.
7. Independent structural classification and freeze.
8. Numeric reveal.
9. Run fixed evaluator.

## Key decision after mechanism reveal

Possible statuses:

### PASS
All preregistered conditions hold.

Action:
- proceed to portfolio/NAV aggregation;
- build analyst product;
- only then consider equity event study.

### EXPLORATORY / INCONCLUSIVE
Point improvement exists but statistical/robustness gates fail.

Action:
- retain research tool;
- collect live data;
- do not claim alpha.

### UNDERPOWERED
Fewer than 25 continuing independent clusters.

Action:
- report honestly;
- decide whether outcome-blind universe expansion is worth the engineering cost.

### FAIL
ShadowNAV does not beat persistence.

Action:
- close trading mechanism;
- retain private-credit data/monitoring product.

## Questions intentionally deferred

- equity returns;
- transaction costs;
- NAV aggregation;
- PIK/non-accrual model;
- manager/appraiser features;
- universe expansion;
- LLM agents/UI.

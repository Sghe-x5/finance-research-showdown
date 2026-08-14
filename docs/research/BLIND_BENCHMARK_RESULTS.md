# Blind Measurement Benchmark Results

## Research boundary

The independent human consensus was frozen in commit `f6abde5700ae1afc20d342cad335112fdd156817` before the private design mappings were opened. The mappings were read only from ignored local files, their SHA-256 values were verified, and no row-level hidden mapping is published here. Human labels were not changed.

This is a measurement benchmark only. No ShadowNAV target outcome, target same-quarter mark, stock return, or target-error metric was opened or calculated. The fund universe was not expanded, no nowcast sample was frozen, and no results tag was created.

## Facility benchmark

The primary model-positive stratum contained 60 hidden `predicted_same_facility_high` pairs. Human consensus classified 58 as the same facility, 2 as definite false positives, and 0 as uncertain.

- Conditional precision among resolved pairs: **96.7%** (58/60).
- Strict confirmation rate over all 60 model-positive pairs: **96.7%**.
- Definite-resolution coverage: **100.0%**.
- Human-uncertain/abstention rate: **0.0%**.
- Wilson two-sided 95% interval for conditional precision: **88.6%–99.1%**.
- Exact one-sided 95% lower bound: **89.9%**.
- Status: **MEASUREMENT_INCONCLUSIVE_REQUIRES_HUMAN_INTERPRETATION**.

The literal point-estimate precision gate passed: 58/60 = 96.7%. A strict statistical guarantee that precision is at least 95% was **not** established: the exact one-sided 95% lower bound is 89.9%. The matcher may therefore be used for confirmatory research only after human review of every included movement event; autonomous production precision of at least 95% is not claimed. An uncertain human consensus is not silently converted into either a true or false positive: it lowers coverage and remains in the strict denominator.

### Manager split within the model-positive stratum

| Relationship | Rows | TP | Definite FP | Uncertain | Conditional precision | Coverage |
|---|---:|---:|---:|---:|---:|---:|
| Same manager | 49 | 47 | 2 | 0 | 95.9% | 100.0% |
| Cross manager | 11 | 11 | 0 | 0 | 100.0% | 100.0% |

The cross-manager benchmark was 11/11 confirmed, but the sample is small. Same-manager observations are excluded from the primary ShadowNAV hypothesis. The manager relationship uses the canonical 19-fund manager map. Manager-pair and official-evidence-completeness breakdowns are stored as aggregates in `facility_blind_evaluation.json`; no blind pair IDs or private candidate IDs are exposed.

False-positive composition is reported in `facility_false_positive_audit.csv`. Categories are assigned deterministically from the public official fields, with one primary reason per definite false positive.

Recall is conditional on the generated candidate universe and is not population recall.

## Alias benchmark

The alias file contained 128 rows. Its 37 blank candidate rows are **non-observations**: they are excluded from the 91-row nonblank denominator and are not true negatives.

- Confirmed same-borrower aliases among nonblank rows: **18**.
- Definite nonmatches: **71**.
- Unresolved: **2**.
- Resolved-candidate alias yield: **20.2%**.
- Resolution coverage: **97.8%**.
- Uncertain rate: **2.2%**.

Across the 30 preselected borrower groups, 1 had at least one confirmed alias, 8 had only definite nonmatches, 1 remained unresolved, and 20 had no candidate observation. Confirmed aliases outside exact-name blocking occurred in 1/30 groups, a conservative lower-bound loss rate of 3.3%.

Within the 18 confirmed borrower-alias rows, facility identity was confirmed for 0, rejected for 16, and unresolved for 2.

Recall is conditional on the generated candidate universe and is not population recall.

## Interpretation and next boundary

These outputs validate or reject the measurement layer only. They do not authorize a ShadowNAV target reveal automatically. Any later target reveal still requires a separate human decision, an approved preregistration, adequate power, and the required matching interpretation.

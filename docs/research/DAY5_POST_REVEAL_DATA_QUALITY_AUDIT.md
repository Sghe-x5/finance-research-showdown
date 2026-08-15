# Day 5 post-reveal data-quality audit

Status: **POST-REVEAL EXPLORATORY DIAGNOSTIC — CANNOT CHANGE OFFICIAL DAY 5 STATUS**

The official Day 5 result remains `data_quality_inconclusive`. This audit does not fill, repair, or rerun the frozen outcome file or evaluator.

## Missing continuing rows

| Review ID | Cluster | Borrower | Source → target | Period | Structural identifier | Missing marks | Classification | Recoverable? |
|---|---|---|---|---|---|---|---|---|
| `D5EV_4bcc43807ee299de5de2ca0a` | `D5EC_bdf50a40b8d90ef96b681429` | Real Chemistry Intermediate III | NCDL → BBDC | 2026Q1 | `Real Chemistry Intermediate III, Inc. \| Revolver` | target prior, target current | `source_absent` for both | No, not as FV/principal |
| `D5EV_f438ca82f7a27e794a1837a9` | `D5EC_03ea18827a74bda0ec1f74a2` | Swoop Intermediate III | NCDL → BBDC | 2026Q1 | `Swoop Intermediate III, Inc. \| Revolver` | target prior, target current | `source_absent` for both | No, not as FV/principal |

## End-to-end lineage

The official SEC BDC `soi.tsv` rows contain the facilities and their cost/fair-value facts. They also explicitly disclose principal as zero.

| Borrower | Stage | Prior 2025-12-31 | Current 2026-03-31 |
|---|---|---|---|
| Real Chemistry | Official raw provenance | `2026_02:49094`, accession `0001379785-26-000009` | `2026_05:132569`, accession `0001379785-26-000022` |
| Real Chemistry | Raw principal / cost / FV | `0 / -4000 / -4000` | `0 / -4000 / -3000` |
| Real Chemistry | Normalized and aggregated | same values, one lot | same values, one lot |
| Swoop | Official raw provenance | `2026_02:53036`, accession `0001379785-26-000009` | `2026_05:141136`, accession `0001379785-26-000022` |
| Swoop | Raw principal / cost / FV | `0 / -4000 / 0` | `0 / -4000 / 0` |
| Swoop | Normalized and aggregated | same values, one lot | same values, one lot |

The parser preserves all three numeric facts. `economic_facility_v2` preserves the rows, identifiers, one-lot aggregation, zero principal, cost, and fair value. The Phase C mapping selects the same revolver identifier across periods. The mark constructor then correctly leaves `fair_value / principal` blank because its denominator is zero.

## Diagnosis

All four missing mark values are classified `source_absent`: the official source does not provide a nonzero principal denominator from which the frozen FV/principal mark can be computed. This is not `parser_loss`, `join_loss`, `aggregation_loss`, `unit_normalization_issue`, or `structural_mapping_issue`.

The source does contain cost and fair value, but substituting an FV/cost measure or treating a zero-principal revolver as a special categorical state would change the frozen outcome definition. Such alternatives may be designed prospectively; they are not repairs to Day 5.

Operationally, a future pipeline should detect zero-principal facilities before sample freeze and route them to an explicit non-mark state. It should also avoid inferring “funded” solely from the absence of an “unfunded” word when principal is zero. Neither change is applied to the official experiment.

The row-level reproducible evidence is in `data/day5_post_reveal/missing_mark_root_cause.csv`.

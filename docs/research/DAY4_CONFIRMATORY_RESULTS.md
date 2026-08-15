# Day 4 Confirmatory ShadowNAV Results

## Frozen evaluator status

The frozen evaluator returned:

`exploratory_inconclusive`

This status is reported without override or reinterpretation. The power guard passed, but two of the six simultaneous PASS criteria were false; therefore the evaluator did not return `pass`.

The authoritative machine output is [`data/day4/confirmatory_results.json`](../../data/day4/confirmatory_results.json), SHA-256 `73fbd25f16457a4b4f7c65e71054bbbe4dc678639112833a2cba54db496eb2c3`.

## Reveal integrity

- Frozen evaluator self-hash verification: **passed**.
- Evaluator SHA-256: `bcea297f43603316d4d3bc5fef9762bc2749eaddf36a3253222af66e8f132615`.
- Exact revealed-to-frozen 37-ID verification: **passed**.
- Numeric structural fields exactly matched the frozen Phase C consensus: **passed**.
- Revealed-outcomes SHA-256: `275300250ed7a8a85cf27078bbbdcf37086bc2c6a5ab2e8deeacdc658d4909ce`.
- Structural consensus SHA-256: `a64a484f32f79f0053e06f15f2c0557e4198535a163fd29cb2a35fc73d91b768`.
- Structural-freeze commit: `ac843d68e3ca28a28d7162b1868ed0503c26a3b0`.
- Continuing rows missing a required mark: **0**.

## Attrition and power

| Position status | Observations |
|---|---:|
| continuing | 35 |
| unmatched_disappearance | 2 |
| partial_repayment | 0 |
| full_repayment | 0 |
| sale_exit | 0 |
| refinancing_amendment | 0 |
| uncertain | 0 |

- Independent continuing source-event clusters: **32**.
- Unique continuing borrowers: **18**.
- Maximum clusters from one borrower: **5**.
- Minimum cluster guard: 32 ≥ 25 — passed.
- Minimum borrower guard: 18 ≥ 15 — passed.
- Evaluator power status: `power_guard_passed`.

## Primary metrics

| Metric | Frozen evaluator output |
|---|---:|
| Cluster-level MAE B0 | 0.06034552795156249 |
| Cluster-level MAE ShadowNAV | 0.029043301182812512 |
| Mean paired error difference | -0.031302226768749976 |
| Relative MAE improvement | 0.5187165947719493 |
| Borrower-clustered one-sided permutation p | 0.14939850601493984 |
| Borrower bootstrap 95% lower | -0.07246575393431369 |
| Borrower bootstrap 95% upper | 0.0023193058053174094 |

## Six simultaneous PASS criteria

| Criterion | Result |
|---|---:|
| `cluster_mae_sn_below_b0` | true |
| `relative_mae_improvement_ge_10pct` | true |
| `borrower_clustered_one_sided_sign_flip_permutation_p_lt_0_05` | false |
| `borrower_bootstrap_interval_below_zero` | false |
| `leave_one_borrower_out_direction_robust` | true |
| `strict_majority_periods_negative` | true |

All six criteria are required simultaneously. The evaluator therefore returned `exploratory_inconclusive`.

## Leave-one-borrower-out

Every leave-one-borrower-out mean paired error difference remained below zero:

| Omitted borrower | Mean paired error difference |
|---|---:|
| asurion | -0.03209816039677418 |
| athenahealth | -0.03303667906999998 |
| baker tilly advisory | -0.0320709620580645 |
| bamboo us bidco | -0.03230699029677417 |
| broadcast music | -0.033057139293548365 |
| bw | -0.032696663874193524 |
| community brands parentco | -0.032809253759999976 |
| confluent health | -0.03412301175517239 |
| confluent medical technologies | -0.032265830003225776 |
| dealer tire financial | -0.032095844958064494 |
| forescout technologies | -0.03412594370666664 |
| icefall parent | -0.0328914622096774 |
| imprivata | -0.03291305796774191 |
| next holdco | -0.032331714348387074 |
| physician partners | -0.029105721328571404 |
| pluralsight | -0.006383003007407384 |
| realpage | -0.03419644974137928 |
| xplor t1 | -0.032068606990322567 |

## Period direction

| Untouched period | Mean paired error difference | Negative |
|---|---:|---:|
| 2024Q1 | -0.025527992300000024 | true |
| 2024Q2 | -0.07379220340909086 | true |
| 2024Q3 | 0.009072799962500072 | false |
| 2024Q4 | -0.04742310989999998 | true |
| 2025Q1 | 0.014699647199999832 | false |
| 2025Q2 | -0.00003201269999997258 | true |

- Negative periods: **4/6**.
- Strict majority negative: **true**.

## Frozen-boundary confirmation

The Phase D run did not change the frozen included sample, Phase A consensus, Phase C consensus, final preregistration, evaluator, formula, threshold, or human label. Both unmatched-disappearance rows remain in the 37-row revealed-outcome file. No results tag was created.

# Day 3 final pre-reveal machine report

Date: **2026-08-14**

Branch: `research/day3-measurement-repair`

Starting commit: `00ee149b3708d6d24c546d9322e8993de82f3ee5`

## 1. Machine phase boundary

This stage extended calendar coverage and measured planning power. It did not
create or alter a frozen nowcast sample, inspect target same-quarter outcomes,
compute target errors, enter blind labels, reveal outcomes or create a tag.
The Day 1 and Day 2 tags remain unchanged.

## 2. Reporting-order extension

`data/day3/reporting_order_extended.csv` contains all 19 funds for every report
period from 2023Q4 through 2025Q3: **152/152 expected rows, 152 verified, zero
missing**. Explicit missing rows remain part of the schema and tests even though
none were needed in this run.

| report period | verified / expected | periodic fallback |
|---|---:|---:|
| 2023Q4 | 19 / 19 | 11 |
| 2024Q1 | 19 / 19 | 13 |
| 2024Q2 | 19 / 19 | 11 |
| 2024Q3 | 19 / 19 | 13 |
| 2024Q4 | 19 / 19 | 12 |
| 2025Q1 | 19 / 19 | 14 |
| 2025Q2 | 19 / 19 | 13 |
| 2025Q3 | 19 / 19 | 13 |

Candidate search used period end through +120 calendar days; 20–80 days was
diagnostic only. Filing lags were 14–81 days, median 37.5 days. Sixty-four
scheduling candidates were rejected. The existing verified 2025Q1–Q3 event
selections and timestamps were preserved.

The source information timestamp is `max(verified results timestamp, SOI
acceptance)`. No earlier EX-99 timestamp is claimed unless that exhibit exposes
the exact facility mark. In this run the mark-public evidence is the SOI
acceptance.

## 3. Movement counts by period

Movement is defined only on `economic_facility_v2` as
`abs(source_current_mark - source_prior_mark) >= 0.005`. All eleven development
borrowers are excluded in every period.

| report period | eligible | computable delta | movement observations | unique movement facilities | unique borrowers | window p25 / median / p75 days |
|---|---:|---:|---:|---:|---:|---:|
| 2023Q4 | 0 | 0 | 0 | 0 | 0 | n/a |
| 2024Q1 | 24 | 20 | 11 | 10 | 9 | 5.77 / 6.96 / 7.94 |
| 2024Q2 | 31 | 27 | 14 | 13 | 9 | 6.97 / 6.97 / 8.96 |
| 2024Q3 | 33 | 30 | 9 | 8 | 7 | 7.04 / 7.04 / 8.01 |
| 2024Q4 | 9 | 8 | 1 | 1 | 1 | 7.20 / 7.20 / 21.99 |
| 2025Q1 | 13 | 12 | 2 | 2 | 2 | 2.00 / 6.93 / 8.93 |
| 2025Q2 | 10 | 10 | 3 | 3 | 3 | 1.98 / 6.97 / 8.45 |
| 2025Q3 | 11 | 11 | 4 | 4 | 3 | 2.00 / 2.00 / 7.04 |

2023Q4 has calendar coverage but cannot produce deltas because the eight
archives do not contain the required 2023Q3 prior positions. 2025Q3 remains the
development period and is excluded from the guard.

## 4. Power-guard result

Untouched independent movement facilities total **37**, exceeding the planning
guard of 20. Therefore `power_guard_passed_for_planning = true`. This is not
freeze or reveal permission: blind matching review and an approved
preregistration v3 remain mandatory.

## 5. Eligibility bottleneck

The first-loss funnel uses 1,410,180 directional source-facility/other-listed-
target possibilities and does not read target-current positions. The leading
losses are limited 19-fund overlap (49.763%) and weak XBRL facility tagging
(42.886%); borrower matching is third (6.754%).

> Primary bottleneck is the limited 19-fund universe, accounting for approximately 49.8% of otherwise possible observations.

## 6. Universe expansion estimate

The eight official SEC archives contain **186 unique BDC CIKs**. No additional
fund was inserted into the working sample.

| screen | count |
|---|---:|
| CIKs with at least 100 aggregated facilities | 163 |
| spread completeness at least 50% | 123 |
| maturity completeness at least 50% | 78 |
| both spread and maturity at least 50% | 60 |
| recommended later additions | 87 |
| additional exchange-ticker targets | 21 |
| additional unknown/non-listed source candidates | 66 |

Estimated candidate-pair multiplier is **4.939×**. Unique source-facility
movement planning estimates are **1,308 conservative / 1,917 base / 1,925
optimistic**, versus 37 currently eligible movements. These are expansion
screening estimates, not confirmatory observations: added funds use periodic
filing acceptance as a timing proxy until their results calendars are verified,
and independent-event growth may be materially lower after blind matching and
manager/borrower dependence controls.

## 7. Japan demotion under current constraints

The Japan track is demoted to a live-data product under current constraints.
Historical indexing remains viable, but the frozen sample produced TDnet 0/20,
Wayback 0/20 and issuer IR was not executed at scale; J-Quants access was
blocked at CDN level from the researcher region. No scalable legal path was
demonstrated under current access and budget constraints. This is not a claim
that no legal path exists and does not declare the track dead.

Reactivation requires working J-Quants access, licensed historical TDnet,
institutional data access, scalable issuer-IR recovery with acceptable
licensing, or prospective live collection. Retained assets include the
2023–2026 TDnet index, timestamps, event IDs and classes, 4,448 raw and 3,999
clean valid-window revision events, and the potential for a live
English-normalized event pipeline.

## 8. Files waiting for human blind review

- `data/day3/blind_facility_pairs_v2.csv` — SHA-256
  `98876afb05fc9d9f1ff0fefad93f461762d4e297f3454d9c64fc8e242ad47d4f`;
- `data/day3/blind_alias_candidates.csv` — SHA-256
  `d37f5daeb4eb6cee9e4ddb2e7690978a6ac899c30305b4fda268bb7424a8b64e`.

Both files, their ignored private keys and their sample compositions are
unchanged from commit `00ee149`. No labels were entered.

## 9. Actions explicitly prohibited

- no new freeze;
- no reveal or target-error calculation;
- no results tag;
- no blind adjudication;
- no automatic expansion of the fund universe;
- no flagship selection based solely on the planning guard.

## 10. Exact next human decision

ChatGPT and Claude independently label the locked facility benchmark and the
alias file, reconcile disagreements, and evaluate blind precision. Humans then
approve or reject preregistration v3 and decide whether the expansion estimate
justifies another ingestion round. A new freeze is possible only if blind
precision passes, movement power remains at least 20 and preregistration v3 is
approved.

> ShadowNAV has sufficient pre-reveal planning power, but no freeze or reveal is authorized until blind matching review and preregistration v3 approval.

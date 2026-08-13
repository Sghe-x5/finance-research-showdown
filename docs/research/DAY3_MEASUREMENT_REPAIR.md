# Day 3 measurement repair — pre-reveal status

Date: **2026-08-14**

Branch: `research/day3-measurement-repair`

Fixed seed: `20260813`

## Boundary

This branch repairs measurement and freezes review artifacts. It does **not**
create a new nowcast sample, reveal target outcomes, finalize preregistration
v3, or create a results tag. The Day 2 frozen sample remains byte-identical and
is retained as a failed pilot.

## ShadowNAV

### Q4 diagnosis

The SEC archive label is the filing-acceptance quarter, not the investment
position quarter. The `2025q4` archive contains filings accepted in Q4 for
positions at 2025-09-30. It cannot provide 2025-12-31 positions; those require
the later `2026q1` archive. The Day 2 zero for 2025Q4 was therefore a coverage
interpretation error, not a lost eligible-row bug.

### Expanded official history and aggregation

| stage | result |
|---|---:|
| SEC acceptance archives | 2024Q1–2025Q4 (8) |
| Raw SOI rows in 19-fund universe | 268,080 |
| Normalized rows | 201,164 |
| Aggregated economic-facility rows | 151,284 |
| Current-period aggregated facilities | 79,200 |
| Borrower-blocked candidate pairs | 25,628 |

Raw ZIPs and normalized/aggregated caches remain outside Git. Git contains the
official URLs, retrieval timestamps, sizes, SHA-256 values, parser/aggregation
metadata and deterministic code.

The economic-facility unit is BDC × position quarter × normalized borrower ×
debt/equity × facility type × lien × currency × reference-rate family × 25 bp
spread bucket × maturity month × funded status. Lots within that unit are
summed; funded/unfunded, currencies, revolvers and term loans remain separate.

### Matching benchmark

The Day 2 100%/100% statistic is invalid as an independent benchmark because
the adjudication defaulted manual labels to predicted labels. It is now marked
as an upper bound by construction.

The replacement blind file contains 60 unlabeled pairs. Before sampling, 1,502
pairs involving already viewed development borrowers were excluded: PetVet,
MRI Software, Anaplan, Viant, Hyland, Fortis, PPV, Ping Identity and
Pye-Barker. Predicted label, confidence, evidence and match-feature columns are
absent.

- blind ID hash: `b748cd5b992e4ffcb8e9d8c95d745ffbe2ab5f58330256452ca53b174bf03a1f`;
- blind file hash: `3e3cff65e5c5a85b4fc5b3bbf115727f42cc14459a54d260414b8d90d414b8d7`;
- labels entered: **0/60**;
- measured precision/recall: **pending blind human labels**.

The alias-recall review separately fixes 30 random ARCC borrowers and 80
review rows against OBDC/NMFC. It contains no target outcomes and no manual
labels yet.

### Movement power guard

Movement is `|source aggregated-facility mark change| >= 0.5 pp`. Counts below
are unique source-facility events among pre-reveal eligible source→target
observations. Eligibility reads source current, source prior and target prior;
it never reads the target same-quarter outcome.

| period | classification | eligible IDs | movement eligible IDs | unique movement source facilities |
|---|---|---:|---:|---:|
| 2025Q1 | untouched target outcomes | 29 | 5 | 5 |
| 2025Q2 | untouched target outcomes | 26 | 6 | 5 |
| 2025Q3 | development; excluded from guard | 26 | 7 | 6 |

Untouched total is **10**, below the preregistration planning guard of 20.
Therefore no reveal should be planned; the fund/reporting-order universe must
be expanded first.

### Day 2 sensitivity correction

Thirteen of 15 old adjusted predictions equal B0. The entire 0.0680-versus-
0.3270 pp advantage is driven by PetVet. Excluding PetVet, both methods have
MAE 0.0696 pp. The adjusted predictor also changed after freeze. The old sample
is not repaired or rerun.

## Japan valid-window gate

The first Day 3 20-ID freeze inherited the old 2023–July 2024 universe. It was
invalidated **before recovery** because the universe was outside the official
J-Quants Free rolling history window. It remains in Git with status
`invalid_window_design`.

The replacement universe is compatible with the stated free-data and price
cutoffs:

| parameter | value |
|---|---|
| Yanoshin window | 2024-09-01 through 2026-05-15 |
| Monthly sequential requests | 21, with 2-second pauses |
| Raw earnings-forecast-revision universe | 4,448 |
| Clean numeric-revision-intent universe | 3,999 |
| Excluded dirty titles | 449 |
| Filter | `業績予想の修正`; exclude dividend, withdrawal/cancellation, undetermined and actual-vs-forecast-difference patterns |
| Fixed sample | 20, seed `20260813` |
| Sample ID hash | `3a510bef6cfe937ac6eb192fef87ff311ac85826927fdd30053a9586f3cdc5a6` |
| Post-April-2025 sample rows | 12/20 |

Frozen IDs:

`JP_Y1043551`, `JP_Y1047004`, `JP_Y1049072`, `JP_Y1054727`,
`JP_Y1055158`, `JP_Y1058619`, `JP_Y1068537`, `JP_Y1071131`,
`JP_Y1100339`, `JP_Y1160334`, `JP_Y1185219`, `JP_Y1186779`,
`JP_Y1195470`, `JP_Y1199291`, `JP_Y1199316`, `JP_Y1200898`,
`JP_Y1203177`, `JP_Y1220656`, `JP_Y1227719`, `JP_Y1241435`.

The freeze was committed before archive attempts. Intermediate results:

| stage | result |
|---|---:|
| Historical TDnet document | 20/20 HTTP 404 |
| Wayback availability | 0/20 snapshots |
| Complete numeric recovery without J-Quants | 0/20 |
| J-Quants V2 `/v2/fins/summary` | 0 requests; pending local `JQUANTS_API_KEY` |
| Gate verdict | **not evaluated** |

New accounts use V2 `x-api-key` authentication. The key is read only from the
environment and is never written to Git. The ≥12/20 gate must not be evaluated
until the J-Quants stage is executed. No 403 was bypassed.

## Current blockers and next authorized action

1. `JQUANTS_API_KEY` must be placed locally in `.env` before the J-Quants stage.
2. Blind facility and alias labels require independent human adjudication.
3. The untouched movement total is 10 < 20, so expand the eligible fund and
   reporting-order universe before any new reveal.
4. Preregistration v3 has not been supplied; the freeze script fails loudly
   without it and hash-locks the evaluator once it exists.

## Sources

- [SEC BDC data sets](https://www.sec.gov/data-research/sec-markets-data/bdc-data-sets)
- [SEC fair-access guidance](https://www.sec.gov/about/developer-resources)
- [J-Quants official plans and V2 authentication](https://jpx-jquants.com/en/)
- [J-Quants official Python client](https://github.com/J-Quants/jquants-api-client-python)
- [Yanoshin TDnet index API](https://webapi.yanoshin.jp/)

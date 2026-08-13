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

The replacement blind file contains 60 unlabeled pairs. Before sampling, 1,549
pairs involving already viewed development borrowers were excluded in every
period: PetVet Care Centers, MRI Software, Anaplan, Viant Medical, Hyland
Software, Fortis Solutions, PPV Intermediate, Ping Identity, Pye-Barker,
Auctane and Medallia. Predicted label, confidence, evidence and match-feature
columns are absent.

- blind ID hash: `c03a68867d9660d13d4c06387b4a7765b38b349069094ca433481b16fc121518`;
- blind file hash: `3e85fbbdaa5a02fddac4edf570c2c30a78257312d7624810accdbadc499ac730`;
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
| 2025Q1 | untouched target outcomes | 16 | 3 | 3 |
| 2025Q2 | untouched target outcomes | 15 | 3 | 3 |
| 2025Q3 | development; excluded from guard | 12 | 4 | 4 |

Untouched total is **6**, below the preregistration planning guard of 20.
Therefore no reveal should be planned; the fund/reporting-order universe must
be expanded first. The corrected per-period counts and formula are copied into
`docs/research/PREREGISTRATION_V3_DRAFT.md`; that file is explicitly not an
approved preregistration or freeze authorization.

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

All 3,999 eligible universe IDs are stored separately in
`data/day3/japan_valid_window_universe_ids.csv`. Re-materialization matched the
original pre-recovery universe hash exactly; the ID-file SHA-256 is
`749b25e06ada86633e244169ee461a100213ae4a8ee96dbfe43c1f7ffe1cd282`.

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

Universe eligibility used only deterministic title/metadata rules before any
recovery attempt. Numeric availability never affected selection, every frozen
row remains in the denominator and failed rows cannot be replaced.

New accounts use V2 `x-api-key` authentication. The key is read only from the
environment and is never written to Git. Before reconstruction, the pipeline
must fetch and expose a DocType distribution for one frozen company; recovery
is blocked until the revision types are approved. Raw paginated responses are
stored only in an outside-Git cache. Pagination-key cycles fail loudly and HTTP
429 uses bounded backoff.

For a recovered pair, `new` is the approved revision record at the exact event
timestamp. `old` is the latest earlier compatible forecast with the same
security, fiscal dates/length, horizon and consolidated/standalone basis.
Record IDs, timestamps, units, basis, rule and confidence are retained. Missing
unambiguous history is `ambiguous_old_forecast`; when the fiscal-year start lies
before the fixed available-from date it is `prior_outside_window`.

Current status: **Japan gate pending J-Quants execution; 0/20 recovered through
issuer/archives only.** No PASS/FAIL/demotion verdict is permitted until
J-Quants, issuer IR and reproducible archive stages are all complete. Outputs
are marked `private research only` pending a distribution-license review. No
403 was bypassed.

## Current blockers and next authorized action

1. `JQUANTS_API_KEY` must be placed locally in `.env`; then run only the DocType
   probe and review it before authorizing reconstruction.
2. Blind facility and alias labels require independent human adjudication.
3. The untouched movement total is 6 < 20, so expand the eligible fund and
   reporting-order universe before any new reveal.
4. Preregistration v3 has not been supplied; the freeze script fails loudly
   without it and hash-locks the evaluator once it exists.

## Sources

- [SEC BDC data sets](https://www.sec.gov/data-research/sec-markets-data/bdc-data-sets)
- [SEC fair-access guidance](https://www.sec.gov/about/developer-resources)
- [J-Quants official plans and V2 authentication](https://jpx-jquants.com/en/)
- [J-Quants official Python client](https://github.com/J-Quants/jquants-api-client-python)
- [Yanoshin TDnet index API](https://webapi.yanoshin.jp/)

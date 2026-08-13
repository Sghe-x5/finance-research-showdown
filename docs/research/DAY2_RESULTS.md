# Day 2 mechanism-pilot results

Date: **2026-08-13**
Branch: `research/day2-mechanism-pilot`
Fixed seed: `20260813`
Freeze commit: `a495f39`

## Decision

**No flagship is selected.** Both tracks remain alive, but neither has yet
passed the full preregistered mechanism gate.

ShadowNAV produced a valid frozen pilot. A strict exact-facility matcher passed
its locked precision gate, but the naive earliest-co-holder signal lost to
target persistence. A source/target prior-bias adjustment looked much stronger,
but the 15 IDs contain four repeated XBRL slices and only 11 unique
borrower/source/target clusters. That adjusted result is therefore an
engineering clue, not a flagship-grade finding.

Japan produced a valid frozen failure-denominator pilot. The eight supplied
numeric seeds were retained, but independent IRBank validation was blocked by
HTTP 403 and all 32 newly sampled historical TDnet links returned 404. The
result is 8/40 provisional recovery, not the earlier 8/8 success story.

## 1. ShadowNAV

### 1.1 Official SEC inputs and provenance

The downloader discovered archive links from the official SEC BDC data-set
page; it did not assume filenames. The page exposed quarterly archives rather
than the “relevant monthly files” anticipated in the execution prompt. The
smallest available pilot was therefore 2025 Q3 and 2025 Q4. No 2026 Q1 archive
was linked when retrieved.

| archive | ZIP bytes | SHA-256 | members | schema |
|---|---:|---|---:|---|
| 2025 Q3 | 30,581,984 | `b35d0a3919bfc120562518ccfc3db613e1346711ccb607bf4c7dfeaf5d8d95a7` | 10 | valid |
| 2025 Q4 | 34,131,811 | `78edc8f08e4e5f58e5b1da413140b49b5c2b62ad0bba757affea61e3de47cdbd` | 10 | valid |

Each archive contained `datasets/sub.tsv`, `soi.tsv`, the supporting XBRL
tables, `readme.htm`, and metadata. The raw ZIPs and the 41 MB normalized cache
remain outside Git. Git contains URLs, retrieval timestamps, member inventory,
sizes, CRCs, header hashes and archive hashes in `data/day2/raw_manifest.csv`.

The parser joined `sub.tsv` to `soi.tsv` on `adsh` and used `accepted` as the
information timestamp. It never used period end as the availability time.

| stage | count |
|---|---:|
| Raw SOI rows for the 19-fund universe | 73,845 |
| Normalized investment/facility rows | 54,285 |
| Duplicate normalized IDs removed | 0 |
| Cross-BDC borrower-blocked candidate pairs | 13,672 |

### 1.2 Facility matching benchmark

Candidate generation used borrower normalization only for blocking. It then
compared debt/equity, facility/tranche type, lien, currency, reference-rate
family, spread (25 bp tolerance), maturity (45-day tolerance), funded status,
and acquisition date when present. Principal, cost and fair value were not used
for either candidate generation or adjudication.

The locked benchmark contains 240 pairs. The unlabelled ID-set hash is
`7c06768b13f1c4f27e85662613f50b93338cfa9c15474cd63ea8468ac28a6a69`.
All 240 identifiers and evidence columns were reviewed after locking.

| manual label \ predicted | same facility | same borrower, other facility | uncertain | unrelated |
|---|---:|---:|---:|---:|
| Same facility | 80 | 0 | 0 | 0 |
| Same borrower, other facility | 0 | 90 | 0 | 5 |
| Uncertain | 0 | 0 | 50 | 15 |
| Unrelated | 0 | 0 | 0 | 0 |

For the preregistered high-confidence `same_facility` class: TP = 80, FP = 0,
FN = 0, precision = 100%, recall = 100%. The 95% precision gate passed. This
does not prove perfect population performance; it describes the fixed locked
sample and should be expanded in future work.

### 1.3 Eligibility and frozen nowcasts

The eligibility stage required an exact facility, same quarter end, earlier
source results and SOI acceptance, listed target, and a target position in the
previous disclosed quarter. It retained 45 eligible IDs for 2025 Q3. The
2025 Q4 source archive does not reveal 2025 Q4 positions; it contains Q3 filings
accepted during Q4, so no Q4 nowcast was fabricated.

Fifteen IDs were selected with seed `20260813` and committed before outcomes.

- eligible-ID hash: `5d3a41022b1e115c66faaa65ba5881e67be6c326c972168f5a2655b27a395605`;
- frozen-sample hash: `6932fa6156029562badf9abf98605ce81fd240aee5f723a95dfbbd3dbe7c7c5f`;
- freeze commit: `a495f39`;
- contaminated fixtures in eligible/frozen estimates: **0**.

No missing, ugly or repeated frozen ID was replaced after reveal. Four IDs are
repeat XBRL slices, leaving 11 unique borrower/source/target clusters. The
statistics below remain observation-ID statistics exactly as frozen.

### 1.4 Frozen baseline results

Outcome is target same-quarter FV/principal. Errors are percentage points of
mark. B1 could not be computed because the two downloaded archives did not
provide the required two clean prior target marks for frozen facilities.

| baseline | n | MAE pp | RMSE pp | median AE pp |
|---|---:|---:|---:|---:|
| B0 target unchanged | 15 | 0.3270 | 0.7668 | 0.0000 |
| B1 target momentum | 0 | — | — | — |
| B2 median already-filed exact co-holders | 15 | 0.3901 | 0.7775 | 0.0000 |
| B3 earliest exact co-holder | 15 | 0.8101 | 1.6034 | 0.0000 |
| B4 prior-quarter cross-lender median | 15 | 0.5648 | 1.0366 | 0.0000 |
| Source mark adjusted by prior source-target gap | 15 | 0.0680 | 0.2348 | 0.0000 |

By reporting window, B3 MAE was 1.7879 pp versus B0 0.5004 pp for four 1–3 day
IDs; for eleven >3 day IDs, B3 was 0.4546 pp versus B0 0.2640 pp. No frozen ID
had a window of one day or less.

No PIK, non-accrual, restructuring or disappearance transition occurred in
the 15 frozen IDs, so categorical prediction could not be evaluated.
Same-manager/JV and common-appraiser exclusions were not computable from the
flat-file fields and remain explicit blockers.

**Interpretation:** the naive “copy the first reporter” rule failed this pilot.
Persistent source-target valuation bias appears important, consistent with the
two contaminated fixtures, but the adjusted result needs a deduplicated,
clustered frozen sample before it is treated as evidence.

### 1.5 Quarantined fixtures

`AUCTANE_ARCC_BXSL_2025Q4` and `MEDALLIA_BXSL_FSK_2025Q4` remain calculation
and parser fixtures only. Tests reproduce their supplied errors, but neither
case appears in the candidate estimate, eligible sample, frozen sample or
baseline metrics.

Scheduling regressions are also preserved: OBDC 2025Q2 on 2025-07-01, GBDC
2025Q2 on 2025-07-07, and FSK's January 2026 Q4 scheduling language are not
classified as results.

## 2. Japanese Language Wall

### 2.1 Locked sample

The historical Yanoshin universe was restricted to corporate earnings-forecast
revision titles (`業績予想の修正`) from the preregistered historical periods. The
deterministic universe contained 678 events. The fixed sample contains the
eight supplied seeds plus 32 randomly selected events, for n = 40.

- seed: `20260813`;
- locked event-ID hash:
  `5cc23bf6b10c149b16d479c455db8cf8df20aea1eec70e4d32cc3f243d30bbe4`;
- failures retained: 32;
- replacements after recovery: 0.

### 2.2 Recovery result

| status | events | rate |
|---|---:|---:|
| Supplied numeric seeds retained provisionally | 8 | 20% |
| New sample rows not recovered | 32 | 80% |
| Total | 40 | 100% |

For all 32 new rows, the old Yanoshin/Tdnet document URL resolved to a 404.
J-Quants recovery was not configured because no entitlement/credentials were
supplied. IRBank returned HTTP 403 to the validation probe; no evasion or bulk
copying was attempted. Wayback/other archive recovery was therefore recorded as
not attempted in this bounded pilot. Every source stage and reason is retained
in `data/day2/japan_recovery_attempts.csv`.

The eight seed values were not silently accepted as independently verified.
Their rows are marked `recovered_provisional`, and independent validation is
explicitly flagged `blocked_http_403`. This prevents the supplied 8/8 seed from
being reported as a representative recovery rate.

IRBank is a third-party recovery source. Its licensing/redistribution terms
were not cleared in this pilot; the site also denied automated validation.
Public release of derived data remains gated on a licensing/ToS review. No raw
IRBank page content is stored in Git.

### 2.3 Treatment status

None of the first ten locked rows has a reproducible complete set of market
segment, English document status/timestamp/lag, prior bilingual behavior and
foreign ownership at the event date. Treatment completion is therefore 0/10
(0%). No price event study was run.

## 3. Gates and blockers

| gate | result |
|---|---|
| Official SEC download/provenance | Pass for 2025 Q3/Q4 |
| Strict facility matching precision ≥95% | Pass: 100% on locked n=240 |
| Frozen ShadowNAV sample before outcomes | Pass: n=15, commit `a495f39` |
| Naive early co-holder beats B0 | Fail: 0.8101 pp vs 0.3270 pp MAE |
| Deduplicated independent ShadowNAV sample | Blocked: 4 repeated XBRL slices |
| B1 two-quarter momentum | Blocked by insufficient period depth |
| Manager/JV/appraiser exclusions | Not observable in current flat files |
| Japan 30–50 fixed sample | Pass: n=40 |
| Independent numerical recovery | Blocked: old PDFs 404, IRBank 403, no J-Quants credentials |
| First ten treatment fields | Fail: 0/10 complete |
| Japan price event study | Correctly not started |

## 4. Day 2 conclusion

No flagship should be chosen from these results. ShadowNAV has the stronger
mechanism infrastructure and passed the matching gate, but its naive signal
failed and its promising bias adjustment needs a newly frozen deduplicated
sample. Japan retained its historical universe but did not clear reproducible
numeric recovery or treatment classification. Day 3, if authorized separately,
should address those exact blockers; this Day 2 branch does not begin it.

## Sources

- [SEC Business Development Company data sets](https://www.sec.gov/data-research/sec-markets-data/bdc-data-sets)
- [SEC developer fair-access guidance](https://www.sec.gov/about/developer-resources)
- [Yanoshin TDnet Web API](https://webapi.yanoshin.jp/)
- [IRBank](https://irbank.net/)

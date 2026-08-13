# DAY 2 RESEARCH MEMO

Date: 2026-08-13
Status: exploratory mechanism work; no flagship selected.

## Executive conclusion

Both tracks remain alive, but today produced a more nuanced result than “one project won.”

- **ShadowNAV:** exact same-quarter facility information can be highly useful, but a naive rule that copies the earliest co-holder’s mark is not uniformly superior to persistence. Two manually inspected cases split one-to-one. The important discovery is not an alpha result; it is a model-design constraint: strict facility matching and persistent lender/appraiser bias are essential.
- **Japan Language Wall:** the historical Yanoshin index’s dead PDF/XBRL links are no longer a complete blocker. For all eight investigated forecast-revision rows in the fixed Day 1 seed, old/new revenue and profit guidance could be recovered from IRBank pages. However, market segment, English treatment, foreign ownership and prices still have to be reconstructed before the language hypothesis can be tested.
- No flagship should be selected today. The BDC examples are contaminated by manual outcome inspection, and the eight Japanese events are a fixed seed rather than a random representative sample.

## 1. ShadowNAV: what was tested

The primary research question remains:

> Does information in an earlier BDC’s public same-quarter disclosure improve the prediction of a later-reporting listed BDC’s still-unpublished mark for the exact same private-credit facility?

The SEC’s official BDC data sets provide XBRL-derived schedules of investments in flat-file form, including investment-level attributes and acceptance metadata. This makes a scalable deterministic pipeline feasible without scraping every HTML table manually.

### Critical data lesson

A borrower name is not a facility identifier.

One borrower may have:
- several lien levels;
- term loans and revolvers;
- funded and unfunded pieces;
- multiple currencies;
- distinct spreads;
- different maturities;
- several acquisition-date slices;
- PIK and cash-pay variants.

Therefore, a valid observation must use a strict facility fingerprint. Loose borrower matching would create false predictive power from unrelated tranches.

## 2. Quarantined ShadowNAV examples

These two examples were manually inspected before a random sample was frozen. They are useful only as parser and arithmetic fixtures.

### 2.1 Auctane: ARCC → BXSL, 2025Q4

Matched facility:
- first-lien senior secured loan;
- SOFR + 5.75%;
- maturity October 2028.

Source ARCC mark:
- principal: $143.4m;
- fair value: $143.4m;
- mark: 100.00%.

BXSL prior-quarter aggregate:
- par: $281.570m;
- fair value: $276.643m;
- mark: 98.2502%.

BXSL reported 2025Q4 aggregate:
- par: $281.570m;
- fair value: $277.347m;
- mark: 98.5002%.

Errors:
- unchanged-target baseline: 0.2500 percentage points;
- ARCC source mark: 1.4998 percentage points.

Result:
- the early source was materially worse than the unchanged target baseline.

Interpretation:
- lender-specific valuation policy, information rights, appraiser, entry history or tranche economics can create persistent mark differences;
- “first report equals truth” is not a valid model.

### 2.2 Medallia: BXSL → FSK, 2025Q4

Matched facility:
- first lien;
- SOFR + 6.50%;
- 4.00% PIK component;
- maturity October 2028.

BXSL early source aggregate:
- par: $396.008m;
- fair value: $307.896m;
- mark: 77.7499%.

FSK prior-quarter:
- par: $232.9m;
- fair value: $212.5m;
- mark: 91.2409%.

FSK reported 2025Q4:
- par: $234.6m;
- fair value: $184.7m;
- mark: 78.7298%.

Errors:
- unchanged-target baseline: 12.5111 percentage points;
- early-source mark: 0.9798 percentage points.

Result:
- the early source improved absolute error by about 92.2%.

Interpretation:
- the first-reporter mechanism can be economically powerful for distressed or fast-repricing facilities;
- the signal must be tested over a frozen random sample, not selected dramatic cases.

## 3. ShadowNAV implication

The correct initial model hierarchy is:

1. unchanged target mark;
2. target own mark momentum;
3. median already-filed exact co-holders;
4. earliest exact co-holder;
5. source mark adjusted for persistent source-target bias;
6. only then ML.

An agentic system is not justified unless it beats the simple baselines out of sample.

The first scientific gate is exact-facility matching precision of at least 95% on a locked manually labelled set.

## 4. Japan: numeric-revision recovery

The tested historical Yanoshin index contains event titles and timestamps, but old document links returned 404. Day 2 investigated whether the old/new numerical guidance could be reconstructed elsewhere.

All eight investigated fixed seed events were recoverable through IRBank pages:

| Code | Issuer | Revenue | Operating profit | Ordinary profit | Net income |
|---|---|---:|---:|---:|---:|
| 2294 | Kakiyasu | 38,700 → 37,000 | 3,050 → 2,400 | 3,050 → 2,400 | 1,900 → 1,500 |
| 2173 | Hakuten | 11,000 → 12,900 | 400 → 690 | 370 → 695 | 250 → 390 |
| 3657 | Pole To Win HD | 47,113 → 46,217 | 1,744 → 644 | 1,776 → 788 | 440 → -514 |
| 7347 | Mercuria HD | 6,700 → 5,800 | 2,450 → 1,000 | 2,450 → 1,200 | 1,700 → 800 |
| 7494 | Konaka | 71,194 → 70,015 | 1,414 → 683 | 1,593 → 887 | 777 → 85 |
| 7561 | HURXLEY | 44,500 → 47,335 | 1,650 → 2,259 | 1,750 → 2,561 | 1,400 → 2,038 |
| 7829 | Samantha Thavasa Japan | 26,119 → 23,640 | 430 → -1,050 | 241 → -1,225 | 326 → -1,140 |
| 1887 | Japan National Land Development | 149,000 → 139,000 | 6,500 → -5,600 | 6,500 → -5,700 | 4,600 → -3,800 |

This is a preliminary 8/8 recovery result, not a representative success-rate estimate.

### What remains unresolved

Before a Japan event study, each event still needs:
- market segment at event time;
- Japanese publication timestamp;
- English full / summary / none;
- English timestamp and lag;
- prior bilingual behavior;
- foreign ownership at event time;
- deterministic linkage to daily prices.

IRBank is a third-party source. A public product should store normalized derived fields, source URLs and evidence, not republish raw content. Licensing and redistribution conditions must be reviewed.

## 5. Comparative status

### ShadowNAV

Strengths:
- direct same-asset, same-quarter accounting ground truth;
- official free SEC data;
- history exists now;
- strict falsifiable baselines.

Risks:
- co-holder monitoring is already commercialized;
- lender-specific bias may dominate the source signal;
- position persistence and exact tranche matching are difficult;
- stock alpha may be fully priced even if mark nowcasting works.

### Japan

Strengths:
- numeric-event history appears recoverable;
- thousands of forecast revisions exist;
- a fresh institutional treatment exists around April 2025;
- a normalized English event dataset retains value at null.

Risks:
- third-party recovery and licensing;
- English treatment reconstruction;
- Prime/Standard confounding;
- daily data cannot detect a purely intraday effect.

## 6. Day 2 decision

No project is selected.

Proceed with:

1. official SEC BDC flat-file parsing;
2. strict facility matching benchmark;
3. frozen random ShadowNAV sample before outcomes;
4. expansion of Japan numeric recovery to 30–50 fixed events;
5. event-level English-treatment reconstruction before prices.

The first track to produce a reproducible out-of-sample improvement over a strong simple baseline, with cleaner licensing and a faster path to live ground truth, should become the flagship.
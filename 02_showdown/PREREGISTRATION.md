# PREREGISTRATION V2 — ShadowNAV vs Japanese Language Wall

Статус: **заморозить коммитом до просмотра Day 2 outcomes**.

## A. ShadowNAV

### A1. Primary hypothesis

For exact same facility `f`, quarter-end `Q`, early source `s` and later target `j`:

> Information available after the first public results/NAV disclosure by `s`
> improves prediction of `j`'s still-unpublished same-quarter `FV/par` relative
> to point-in-time naive baselines.

### A2. Unit of observation

`facility_id × quarter_end × source_bdc × target_bdc`

Required:

- source first results timestamp < target first results timestamp;
- exact facility match;
- target held facility in previous disclosure;
- only information public before target cutoff;
- amendments kept as new records, not overwritten.

### A3. Primary metric

Out-of-sample MAE on target `FV/par`.

Also report:

- RMSE;
- median absolute error;
- interval coverage;
- results by window length;
- results excluding same manager/JV/common appraiser where observable.

### A4. Baselines

- B0: unchanged target mark;
- B1: target own mark momentum;
- B2: median of already-filed exact co-holders;
- B3: earliest co-holder only;
- B4: previous-quarter cross-lender median;
- B5: categorical distress flags only.

ML/LLM models proceed only if they beat the best baseline OOS.

### A5. Secondary hypotheses

- H1b: source PIK/non-accrual/restructuring predicts target same-quarter status.
- H2: cross-lender t→t+1 convergence.
- H3: target relative return reacts/drifts on source disclosure date.

H3 benchmark: equal-weighted BDC basket, not SPY. Relative-value only.

### A6. Manual pilot rules

- Build all eligible observations first.
- Fix random seed in the repo.
- Draw sample IDs before viewing target outcomes.
- Do not replace failed/ugly cases.
- Save source/target evidence and exclusion reason.

### A7. ShadowNAV kill criteria for showdown

Track is demoted if any fatal condition holds:

- exact-facility matching precision <95% on locked manual set;
- too few historical eligible observations for reasonable OOS evaluation;
- first-reporter signal does not improve MAE against best naive baseline;
- result disappears after entry-price adjustment;
- result exists only for same-manager/JV/common-appraiser pairs;
- reporter-order placebo/shuffle performs similarly;
- target positions are too unstable to nowcast.

The 10% MAE-improvement level is a practical target, not a scientific law; report
the full effect and uncertainty.

## B. Japanese Language Wall

### B1. Measurement prerequisite

For at least 30–50 historical forecast-revision events, reproducibly obtain:

- old/new numerical forecast;
- publication timestamp;
- segment;
- JP document/evidence;
- EN full/summary/none and lag;
- prices older than J-Quants free delay.

Without numeric content, Japan becomes live-only and loses the historical showdown.

### B2. Primary hypothesis

Post-announcement drift `T+1...T+10` following forecast revisions:

- declines after April 2025 for Prime firms that previously translated late/not at all;
- changes little for already-simultaneous bilingual Prime firms;
- persists more on Standard;
- language-channel effect increases with foreign ownership.

### B3. Primary outcomes

- CAR T+1, T+3, T+5, T+10;
- control for revision magnitude, market segment, size, liquidity, industry,
  event timing and market return;
- document parallel trends before April 2025;
- robustness excluding April–May 2025.

### B4. Known limitation

Daily data cannot detect an effect that disappears within minutes of next open.
A daily null does not prove no intraday language effect; it does weaken the
tradable daily-drift thesis.

### B5. Japan kill criteria for showdown

Track is demoted if:

- old/new numbers cannot be recovered reproducibly;
- event-level English treatment cannot be measured;
- usable history is too short/sparse;
- no price linkage with deterministic event-time;
- all daily adjustment occurs in day 0 with no measurable later drift;
- mechanism does not vary with foreign ownership / prior English behavior.

## C. Flagship selection

Choose one flagship after Day 3 using evidence, not scores.

Priority order:

1. direct new-information → observable future ground truth;
2. usable historical sample and achievable OOS;
3. baseline improvement;
4. data/license robustness;
5. trading window;
6. useful product at null.

If both fail, only then unfreeze reserve hypotheses.

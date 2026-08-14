# Project Timeline and Decision Log

## Stage 0 — Original idea

Initial question: can the next quarterly report be forecast, compared with market
expectations, and used to identify where the market is wrong?

The first architecture became a pre-earnings engine with:
- revenue/EPS/margins/FCF/CapEx/KPI forecasts;
- P(beat), P(revision), P(drift);
- forecastability score and NO TRADE;
- daily point-in-time consensus collection.

Decision: keep this as a product architecture, but it lacked a sufficiently unique
information source as a standalone flagship.

## Stage 1 — Broad search for new mechanisms

Ideas explored:
- AI Reader Distortion / Model Monoculture;
- prompt-injection and hidden-content audits in filings;
- Regulatory Normalization Lag;
- supplier-finance shadow debt;
- government-contract deobligation;
- PowerQueue;
- EU public country-by-country reporting;
- clinical-trial timing;
- prediction-market bases;
- silent XBRL changes.

Decision: do not choose novelty by story alone. Require a concrete slow actor,
free data, observable future ground truth, and a cheap kill test.

## Stage 2 — Two finalists

### ShadowNAV

Same asset, same quarter-end, different disclosure times.

### Japanese Language Wall

Prime Market simultaneous English disclosure from April 2025 versus Standard Market,
with potential daily post-disclosure drift and foreign-ownership interaction.

Decision: run a 72-hour empirical showdown rather than keep brainstorming.

## Day 1

Findings:
- BDC reporting windows were real.
- Several initial dates were false positives caused by scheduling/dividend 8-Ks.
- Non-traded BDCs were usually later, not systematic early sensors.
- Yanoshin historical index existed.
- Historical TDnet PDF/XBRL links often returned 404.

## Day 2

ShadowNAV:
- official SEC BDC flat files ingested;
- 45 eligible pilot nowcasts;
- frozen sample of 15;
- naive earliest co-holder lost to persistence;
- apparent prior-gap result was driven entirely by PetVet;
- repeated XBRL slices invalidated the unit of analysis;
- old matching benchmark was circular.

Japan:
- independent recovery 0/32;
- supplied eight seed rows were not independent validation;
- treatment layer remained unavailable.

Decision: Day 2 is a preserved failed/exploratory pilot, not evidence of alpha.

## Day 3 — Measurement repair

- Created economic facility aggregation v2.
- Extended history and reporting-order calendar.
- Built blind facility and alias benchmarks.
- Human consensus completed before hidden mapping reveal.
- Facility high-confidence positives: 58/60 confirmed.
- Cross-manager positives: 11/11 confirmed.
- Alias expansion added borrower matches but no confirmed same-facility match in that audit.
- Planning set: 37 untouched cross-manager movement facilities.

Decision: proceed to event-by-event human review; no autonomous matcher claim.

## Day 4 — Confirmatory preparation

- Outcome-blind packet created: 40 observations / 37 source clusters.
- Draft preregistration and synthetic-tested evaluator prepared.
- Audit found indirect outcome leakage risk through filing URLs.
- Audit also found the need for a structural non-numeric target-current freeze before marks.

Current decision: sanitize packet and harden two-stage reveal before review or freeze.

# Day 1 findings — reconciled

Date: **2026-08-12**

## Outcome

No flagship was selected. Both projects survive Day 1, with different fatal
measurement gates for Day 2.

### ShadowNAV

- Multi-day reporting-order windows remain after content-based classification.
- The corrected, still-provisional five-quarter listed-BDC distribution is p25 **1.993 days**,
  median **5.999 days**, p75 **12.988 days** (`n=525`; `>1d=451`, `>3d=343`,
  `>5d=291`).
- OBDC `2025-07-01` and GBDC `2025-07-07` were false positives: their EX-99
  exhibits scheduled later releases and contained no quarterly results/NAV.
- The refreshed CSV records period end, exact SEC acceptance timestamp,
  market session, event type, accession, source URL, verification status and
  exclusion reason.
- Exact distribution remains provisional pending a manual check for any earlier
  official IR-only results/NAV releases not represented in SEC exhibits.
- The `non-traded-first` core story is refuted. All 20 pilot observations over
  five complete quarters were later than the listed-BDC median; only niche
  non-traded→very-late-listed cases might remain.
- Calendar order is not a signal. The fatal next gate is exact-facility matching
  and an outcome-hidden manual nowcast against simple baselines.

### Japanese Language Wall

- The Yanoshin historical index returns 4,027–6,216 records for the tested
  2023–2025 ranges when queried with `limit=10000`.
- Forecast-revision title matches range from 229 to 313 in those tests.
- Every tested old PDF and XBRL link returned 404 after redirect. Index/title
  availability must not be described as document availability.
- The fatal next gate is recovering numerical old/new earnings forecasts for a
  reproducible historical sample, plus event-level English-treatment fields.

Dashboard scores, old priors and raw calendar-pair counts are not selection
criteria and must not be used to choose the flagship.

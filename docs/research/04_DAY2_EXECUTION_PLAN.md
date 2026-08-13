# Day 2 execution plan

## Before any manual outcomes

1. Commit/tag Day 1 reconciliation.
2. Fix and regenerate BDC reporting order:
   - exclude scheduling/dividend announcements;
   - verify Item 2.02 / EX-99 / IR results/NAV;
   - store acceptance timestamp and market session.
3. Create a complete eligible-observation list.
4. Fix random seed and sample IDs.
5. Only then open target outcomes.

## Track A — ShadowNAV

### A1. Correct calendar

Known regression cases:

- OBDC 2025Q2 `07-01` must not be results;
- GBDC 2025Q2 `07-07` must not be results.

The script should classify the actual contents of 8-K/exhibit, not take the first
8-K after period end.

Required output columns:

- period_end;
- BDC / CIK;
- first_results_timestamp_utc;
- first_results_timestamp_et;
- market_session;
- event_type;
- 8-K accession;
- EX-99/IR URL;
- 10-Q/10-K accession;
- verification_status;
- exclusion_reason.

Recompute window distribution after correction.

### A2. Manual SOI pilot

Start with several early/late pairs from the corrected calendar. Previous
suggestions such as `GCP→FSK`, `GCP→BXSL`, `OCIC→GBDC`, `ARCC→MFIC` are only
candidates and must be revalidated after calendar correction.

For each pair:

1. locate source and target Schedule of Investments;
2. list shared borrowers;
3. classify:
   - exact same facility;
   - same borrower, different facility;
   - uncertain;
4. compare lien, facility type, rate/spread, maturity, currency, par, cost, FV;
5. record PIK/non-accrual/restructuring;
6. save page/table evidence.

### A3. Manual nowcast

- generate random sample from all eligible exact matches;
- freeze seed and IDs;
- target values hidden until prediction saved;
- compare:
  - unchanged mark;
  - earliest source;
  - median available co-holders if >1;
- report MAE even if ugly.

### A4. Categorical distress

Test PIK/non-accrual first because it is less sensitive to valuation noise.

### A5. Dirty price sanity check

For large source markdowns:

- event date = source first results disclosure;
- target return minus equal-weighted listed BDC basket;
- day 0 / +1 / +3 / until target results;
- exploratory only, not proof.

## Track B — Japan

### B1. Recover document content

For 30–50 forecast revisions, try in fixed order:

1. issuer IR archive;
2. J-Quants statements/financial results;
3. IR Bank or reputable mirror;
4. Wayback;
5. other reproducible archive.

Record source and retrieval success. Do not manually invent old/new values from
titles.

### B2. Event schema

Minimum fields:

- security code;
- issuer;
- market segment;
- JP publication timestamp;
- original title;
- old/new revenue;
- old/new operating profit;
- old/new ordinary profit;
- old/new net income;
- fiscal period;
- direction and magnitude;
- JP evidence URL;
- EN full/summary/none;
- EN timestamp / lag;
- prior bilingual behavior;
- foreign ownership;
- prices and event-time convention.

### B3. Sample discipline

Use one clean event class only. Select events older than the J-Quants 12-week
delay. Keep failures and missing-document cases in the denominator.

## End-of-Day-2 outputs

- corrected `reporting_order.csv`;
- BDC exact-match count and denominator;
- random sample seed + IDs;
- first manual mark predictions saved before outcomes;
- Japan recovery rate for numeric revisions;
- first event-level JP/EN treatment rows;
- updated decision table;
- no flagship choice yet unless one fatal gate clearly fails.

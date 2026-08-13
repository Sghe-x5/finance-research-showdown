# CODEX TASK — DAY 2 MECHANISM PILOT

Repository: `Sghe-x5/finance-research-showdown`
Current frozen Day 1 branch/tag:
- branch: `research/day1-showdown-reconciled`
- tag: `showdown-day1-reconciled-2026-08-12`

Today is **Day 2**. The goal is not to build a product, UI, agent swarm, fine-tune or trading strategy. The goal is to produce the first valid mechanism evidence for the two preregistered tracks:

1. **ShadowNAV**
2. **Japanese Language Wall**

Read first, in this order:

1. `README.md`
2. `DAY1_START_HERE.md`
3. `docs/research/01_DAY1_CANONICAL_FINDINGS.md`
4. `docs/research/03_PREREGISTRATION_V2.md`
5. `docs/research/04_DAY2_EXECUTION_PLAN.md`
6. `02_showdown/SHOWDOWN_TRACKER.md`

Also copy the supplied Day 2 artifacts into the repository under:
- `artifacts/day2/finance_project_day2_tracker.xlsx`
- `docs/research/DAY2_RESEARCH_MEMO.md`
- `docs/research/CODEX_DAY2_PROMPT.md`
- `data/day2/bdc_contaminated_examples.csv`
- `data/day2/japan_numeric_recovery_seed.csv`
- `data/day2/day2_decision_log.csv`

## 0. BRANCH AND FREEZE RULES

1. Do not move or recreate the Day 1 tag.
2. Create and switch to:
   `research/day2-mechanism-pilot`
   from the current Day 1 tagged/head commit.
3. Do not rewrite Day 1 CSVs, workbook tabs or canonical findings in place.
4. Day 2 outputs must be new append-only files with provenance.
5. Use fixed random seed:
   `20260813`
6. Never select examples after viewing target outcomes.
7. The two manually inspected examples below are **contaminated** and must be excluded from every preregistered estimate:
   - `AUCTANE_ARCC_BXSL_2025Q4`
   - `MEDALLIA_BXSL_FSK_2025Q4`
   Keep them only as parser/regression fixtures.

## 1. SHADOWNAV — OFFICIAL SEC FLAT-FILE PIPELINE

The SEC now publishes official BDC XBRL flat files:
`https://www.sec.gov/data-research/sec-markets-data/bdc-data-sets`

Start with the smallest period set sufficient for the pilot:
- 2025 Q3 / relevant monthly files
- 2025 Q4 / relevant monthly files
- optionally 2026 Q1 if time permits

### 1.1 Download and provenance

Implement a deterministic downloader that:

- follows SEC fair-access rules;
- takes `SEC_USER_AGENT` from environment;
- limits requests;
- stores source URL, retrieval UTC timestamp, byte size and SHA-256;
- caches raw ZIPs outside Git;
- writes only manifests/checksums to Git;
- fails loudly on an unexpected schema.

Do not assume archive filenames or TSV names. Inspect each ZIP and log its file inventory first.

### 1.2 Parse the BDC dataset

Join the submission metadata and Schedule of Investments using the SEC accession key (`adsh` or the exact field present in the archive).

Preserve at minimum:

- accession number;
- acceptance datetime;
- CIK / filer;
- period end;
- investment identifier/context;
- borrower raw name;
- investment/facility type;
- lien/seniority if available;
- reference rate;
- spread;
- total interest rate;
- PIK component;
- maturity;
- currency;
- principal/par;
- cost/amortized cost;
- fair value;
- non-accrual / PIK / restructuring flags where tagged;
- source concept and raw row provenance.

Never use period end as information availability time.

### 1.3 Facility matching, not borrower matching

`same borrower` is not a match.

Construct a strict facility fingerprint using, where available:

- normalized borrower;
- debt vs equity;
- facility/tranche type;
- lien/seniority;
- currency;
- reference-rate family;
- spread with a reasonable tolerance;
- maturity with a reasonable tolerance;
- funded vs unfunded;
- origination/acquisition date if disclosed.

One borrower can have several tranches, currencies, revolvers, delayed-draw lines and PIK slices.

Create:

- deterministic candidate blocking;
- pairwise features;
- `same_facility / same_borrower_different_facility / uncertain / unrelated`;
- evidence columns;
- match confidence.

### 1.4 Locked matching benchmark

Before building the full forecasting sample:

1. Generate the candidate-pair universe.
2. Draw a fixed locked sample of at least 200 pairs with seed `20260813`.
3. Save IDs and SHA-256 before labels are entered.
4. Manually adjudicate labels.
5. Report precision, recall and confusion matrix.

Primary gate:
- high-confidence `same_facility` precision must be at least 95%.

Prefer false negatives to false positives.

### 1.5 Eligible same-quarter observations

Build all observations satisfying:

- exact same facility;
- same quarter end;
- source first-results timestamp < target first-results timestamp;
- target is listed for the tradable layer;
- target held the position in the previous available filing;
- source information was public before target cutoff;
- no use of target outcome until prediction is frozen.

The target cutoff is the **first public results/NAV disclosure**, including:
- 8-K Item 2.02 / EX-99;
- official IR earnings/NAV release;
- 10-Q/10-K only if nothing earlier existed.

Keep existing scheduling-announcement regression tests, including:
- OBDC 2025Q2 `2025-07-01` is not results;
- GBDC 2025Q2 `2025-07-07` is not results;
- FSK January 2026 scheduling announcement is not Q4 results.

### 1.6 Freeze the manual nowcast sample

After all eligible IDs exist:

1. Save the full eligible-observation table.
2. Randomly draw 10–20 observation IDs with seed `20260813`.
3. Commit:
   - IDs;
   - seed;
   - generation code;
   - SHA-256 of the frozen sample.
4. Only after that commit, reveal target values.

Do not replace missing, ugly or failed cases.

### 1.7 Baselines and outcomes

Primary outcome:
- target same-quarter `FV/par`.

Baselines:
- B0: target mark unchanged from prior quarter;
- B1: target own mark momentum;
- B2: median of already-filed exact co-holders;
- B3: earliest exact co-holder;
- B4: previous-quarter cross-lender median;
- B5: categorical distress flags only.

Report:
- MAE;
- RMSE;
- median absolute error;
- result by reporting window;
- result after entry-price adjustment;
- result excluding same manager / JV / common appraiser where observable.

ML/LLM models are not allowed until a simple baseline comparison is complete.

### 1.8 Categorical distress

Test separately:

- PIK transition;
- non-accrual transition;
- restructuring / amendment;
- disappearance or repayment of target position.

These may be more robust than continuous fair-value marks.

### 1.9 Quarantined fixtures

Add regression fixtures for the two already inspected examples:

#### Auctane, 2025Q4
- source ARCC: par 143.4, FV 143.4, mark 100%;
- target BXSL prior aggregate: par 281.570, FV 276.643;
- target BXSL actual aggregate: par 281.570, FV 277.347;
- unchanged baseline error ≈ 0.2500 pp;
- source error ≈ 1.4998 pp;
- source was worse.

#### Medallia, 2025Q4
- source BXSL aggregate: par 396.008, FV 307.896;
- target FSK prior: par 232.9, FV 212.5;
- target FSK actual: par 234.6, FV 184.7;
- unchanged baseline error ≈ 12.5111 pp;
- source error ≈ 0.9798 pp;
- source was much better.

These fixtures validate calculations only. They do not enter estimates.

## 2. JAPAN — NUMERIC RECOVERY AND TREATMENT TABLE

The historical Yanoshin index is alive, but tested old document links return 404.

The Day 2 pilot found that the pre-existing seed rows can often be recovered through IRBank. Treat IRBank as a third-party recovery source, not a redistributable primary dataset.

### 2.1 Fixed event sample

Create a deterministic 30–50 event sample from the already identified historical forecast-revision universe.

Rules:

- one event class only: corporate earnings forecast revisions;
- use events older than the J-Quants 12-week free-data delay;
- fix event IDs before recovery attempts;
- retain every failure in the denominator;
- do not replace failed events.

### 2.2 Source hierarchy

Try in this order and record every attempt:

1. issuer IR archive / official PDF;
2. J-Quants or official financial statement data;
3. IRBank or another reputable mirror;
4. Wayback;
5. other reproducible archive.

Store normalized derived fields, source URL and short evidence. Do not mass-copy third-party page content into Git.

Review source licensing/ToS before any public release.

### 2.3 Required numeric schema

For each event:

- security code;
- issuer;
- fiscal period;
- publication timestamp JST;
- old/new revenue;
- old/new operating profit;
- old/new ordinary profit;
- old/new net income;
- direction and percentage changes;
- recovery status;
- source type;
- evidence URL;
- failure reason.

Preserve:
- period length;
- consolidated vs standalone;
- fiscal-year changes;
- units;
- profit metrics crossing zero.

### 2.4 Treatment fields

For the first 10 clean recovered rows, attempt to obtain:

- market segment at event time;
- JP document timestamp;
- English document: full / summary / none;
- English timestamp and lag;
- prior bilingual behavior;
- foreign ownership at event time.

Do not run the price event study until treatment classification is reproducible.

### 2.5 Preliminary seed values to regression-test

The supplied CSV/workbook contains eight recovered seed events:
- 2294 Kakiyasu;
- 2173 Hakuten;
- 3657 Pole To Win Holdings;
- 7347 Mercuria Holdings;
- 7494 Konaka;
- 7561 HURXLEY;
- 7829 Samantha Thavasa Japan;
- 1887 Japan National Land Development.

Validate these values against source pages and flag any discrepancy rather than silently correcting it.

## 3. REQUIRED DAY 2 OUTPUTS

Create:

- `scripts/day2/download_sec_bdc_data.py`
- `scripts/day2/parse_bdc_soi.py`
- `scripts/day2/build_facility_candidates.py`
- `scripts/day2/freeze_match_benchmark.py`
- `scripts/day2/build_eligible_nowcasts.py`
- `scripts/day2/freeze_nowcast_sample.py`
- `scripts/day2/recover_japan_revisions.py`
- tests for each deterministic stage;
- `data/day2/raw_manifest.csv`
- `data/day2/facility_candidates.csv` or Parquet metadata;
- `data/day2/locked_match_sample.csv`
- `data/day2/eligible_nowcast_ids.csv`
- `data/day2/frozen_nowcast_sample.json`
- `data/day2/japan_revision_sample.csv`
- `data/day2/japan_recovery_attempts.csv`
- `docs/research/DAY2_RESULTS.md`
- updated `02_showdown/SHOWDOWN_TRACKER.md`.

Do not commit large raw ZIPs, raw scraped sites or secrets.

## 4. VALIDATION

Run:

- `python -m py_compile` for all Python files;
- `pytest`;
- schema checks;
- duplicate-ID checks;
- timestamp monotonicity checks;
- unit tests for facility aggregation;
- regression tests for Auctane and Medallia calculations;
- security scan for:
  - `.env`;
  - API keys;
  - absolute `/Users/...` paths;
  - personal SEC email;
  - caches;
  - large raw files.

If network access blocks the official SEC download, do not fabricate outputs. Commit the downloader/parser/tests and document the exact blocker.

## 5. COMMIT AND PUSH

Suggested commits:

1. `research: add official BDC facility pipeline and freeze day-2 samples`
2. `research: recover Japanese forecast revisions and record day-2 evidence`

Push branch:
`research/day2-mechanism-pilot`

Do not force-push.

Create annotated tag only after Day 2 outputs are stable:
`showdown-day2-mechanism-2026-08-13`

At the end report:

- branch;
- commit hashes;
- tag;
- tests;
- number of raw BDC rows;
- candidate facility pairs;
- locked benchmark size and precision;
- eligible nowcast count;
- frozen sample IDs/hash;
- Japan sample size and recovery rate;
- first 10 treatment-field completion rate;
- blockers;
- explicit statement that the two contaminated BDC fixtures were excluded.
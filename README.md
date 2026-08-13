# Finance Research Project — Day 1 showdown

Frozen reconciliation date: **2026-08-12**.

The project is a 72-hour evidence-first comparison of two research tracks:

- **ShadowNAV:** whether an early BDC's same-quarter facility mark improves a
  nowcast of a later listed BDC's still-unpublished mark for the exact same
  facility.
- **Japanese Language Wall:** whether post-announcement drift after earnings
  forecast revisions depends on English-disclosure treatment, TSE segment and
  foreign ownership.

No flagship has been selected. Dashboard scores and pre-data priors are not
selection criteria.

## Day 1 status

- Corrected BDC reporting-order windows exist. The current provisional
  distribution across five complete quarters
  and 15 listed BDCs, 525 ordered windows have p25/median/p75 of
  **2.0 / 6.0 / 13.0 days**; 343 exceed 3 days. These are calendar windows, not
  trades or evidence of alpha, and remains provisional until possible IR-only
  releases have been manually checked.
- The core `non-traded-first` story is refuted: the four pilot non-traded BDCs
  generally report after listed BDCs.
- The Yanoshin historical index is alive for the tested 2023–2025 periods.
  Every tested old PDF/XBRL link redirected to a 404, so document availability
  is not established.
- The decisive Day 2 gates are exact-facility overlap for ShadowNAV and
  reproducible recovery of numerical old/new Japanese forecast revisions.

## Canonical reading order

1. [`DAY1_START_HERE.md`](DAY1_START_HERE.md)
2. [`docs/research/01_DAY1_CANONICAL_FINDINGS.md`](docs/research/01_DAY1_CANONICAL_FINDINGS.md)
3. [`docs/research/03_PREREGISTRATION_V2.md`](docs/research/03_PREREGISTRATION_V2.md)
4. [`02_showdown/SHOWDOWN_TRACKER.md`](02_showdown/SHOWDOWN_TRACKER.md)
5. [`02_showdown/reporting_order.csv`](02_showdown/reporting_order.csv)

Historical Claude files live under `docs/research/history/` and are not current
sources of truth.

## Reproduction

SEC requests require a descriptive contact value; copy `.env.example` and set
the variable in your shell without committing the real value:

```bash
export SEC_USER_AGENT="ShadowNAV research your-name@example.com"
python3 02_showdown/day1_bdc_reporting_order.py
```

The script runs sequentially, sleeps between SEC requests, verifies EX-99
content, and writes both `reporting_order.csv` and
`reporting_order_summary.csv`.

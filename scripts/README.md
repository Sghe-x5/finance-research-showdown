# Scripts

The code is organized by research phase rather than as a production package.
Scripts are deterministic, explicit about provenance, and deliberately avoid
agent frameworks or UI layers.

## Day 2 — frozen pilot implementation

`scripts/day2/` preserves the official-SEC downloader, parser, candidate
builder, sample-freeze utilities, and exploratory evaluator used for the Day 2
checkpoint. These files are part of the historical audit trail and should not
be silently upgraded in place.

Important groups:

- `download_sec_bdc_data.py`, `parse_bdc_soi.py` — archive discovery and SOI
  normalization;
- `build_facility_candidates.py`, `freeze_match_benchmark.py` — initial
  candidate and benchmark logic;
- `build_eligible_nowcasts.py`, `freeze_nowcast_sample.py` — original eligible
  and freeze stages;
- `evaluate_nowcasts.py` — exploratory Day 2 calculations;
- `recover_japan_revisions.py` — historical revision recovery pilot.

## Day 3 — current measurement layer

`scripts/day3/` contains corrected, append-only measurement work:

| Stage | Main scripts |
|---|---|
| Official field repair | `audit_field_lineage.py`, `repair_bdc_field_lineage.py` |
| Economic facility unit | `aggregate_facilities.py`, `audit_aggregation_v1.py` |
| Matching and blind export | `build_facility_candidates.py`, `export_stratified_blind_facilities_v3.py`, `export_blind_alias_audit.py` |
| Reporting order and timing | `build_reporting_order_extended.py`, `audit_reporting_fallbacks.py` |
| Pre-reveal eligibility | `build_eligible_nowcasts.py`, `analyze_pre_reveal_power.py`, `count_movement_events.py` |
| Manager and universe audits | `build_manager_overlap_audit.py`, `estimate_universe_expansion.py` |
| Japan gate provenance | `run_japan_valid_window_gate.py`, `run_japan_recovery_gate.py` |

The Day 3 evaluator and freeze utility exist only as guarded future stages. Their
presence does not authorize a new sample freeze or outcome reveal.

## Environment

Install the small test/runtime dependency set from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Networked SEC scripts require `SEC_USER_AGENT`. J-Quants code reads
`JQUANTS_API_KEY` when explicitly authorized. Real values belong in the shell or
an ignored `.env`, never in tracked source.

## Validation

```bash
python -m pytest -q
python -m compileall -q 02_showdown scripts tests
git diff --check
```

Tests are designed to run without downloading raw archives or contacting SEC,
TDnet, Wayback, or J-Quants.

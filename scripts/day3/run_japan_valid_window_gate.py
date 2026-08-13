#!/usr/bin/env python3
"""Valid-window Japan gate: freeze first, archive now, J-Quants only with a key."""

import argparse
import calendar
import csv
import json
import os
import random
import sys
import time
from datetime import date
from pathlib import Path

DAY2 = Path(__file__).resolve().parents[1] / "day2"
DAY3 = Path(__file__).resolve().parent
sys.path.insert(0, str(DAY2))
sys.path.insert(0, str(DAY3))

from common import SEED, canonical_json, sha256_bytes, write_csv, write_json  # noqa: E402
from recover_japan_revisions import forecast_events  # noqa: E402
from run_japan_recovery_gate import (  # noqa: E402
    ATTEMPT_FIELDS, SAMPLE_FIELDS, clean_event, direct_document_attempt,
    recover_from_jquants, wayback_attempt,
)


START = date(2024, 9, 1)
END = date(2026, 5, 15)
SAMPLE_PATH = Path("data/day3/japan_valid_window_sample.csv")
ATTEMPTS_PATH = Path("data/day3/japan_valid_window_attempts.csv")
META_PATH = Path("data/day3/japan_valid_window_meta.json")
SUMMARY_PATH = Path("data/day3/japan_valid_window_summary.json")
LEGACY_SAMPLE_PATH = Path("data/day3/japan_gate_sample.csv")
LEGACY_META_PATH = Path("data/day3/japan_gate_meta.json")


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def monthly_periods(start=START, end=END):
    output = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        first = start if (year, month) == (start.year, start.month) else date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        last = end if (year, month) == (end.year, end.month) else date(year, month, last_day)
        output.append(f"{first:%Y%m%d}-{last:%Y%m%d}")
        month += 1
        if month == 13:
            year += 1
            month = 1
    return output


def invalidate_legacy_window():
    rows = read_rows(LEGACY_SAMPLE_PATH)
    for row in rows:
        row["recovery_status"] = "invalid_window_design"
        row["failure_reason"] = (
            "Superseded before recovery: all source events end by 2024-07-31 and fall outside "
            "the J-Quants Free rolling two-year history window as of 2026-08-14."
        )
    write_csv(LEGACY_SAMPLE_PATH, rows, SAMPLE_FIELDS)
    meta = json.loads(LEGACY_META_PATH.read_text(encoding="utf-8"))
    meta.update({
        "design_status": "invalid_window_design",
        "invalidated_before_recovery": True,
        "invalidated_reason": (
            "Universe ended 2024-07-31; the official J-Quants Free plan exposes only two years "
            "of history with a 12-week delivery delay. Failure would be mechanical."
        ),
        "replacement_window": {"start": START.isoformat(), "end": END.isoformat()},
    })
    write_json(LEGACY_META_PATH, meta)


def freeze(sample_size=20, seed=SEED):
    if SAMPLE_PATH.exists() or ATTEMPTS_PATH.exists():
        raise RuntimeError("Refusing to overwrite the valid-window Japan freeze")
    periods = monthly_periods()
    raw = sorted(forecast_events(periods), key=lambda row: row["event_id"])
    clean = [row for row in raw if clean_event(row)]
    if len(clean) < sample_size:
        raise RuntimeError(f"Need {sample_size} clean events, found {len(clean)}")
    selected = sorted(random.Random(seed).sample(clean, sample_size), key=lambda row: row["event_id"])
    rows = []
    for event in selected:
        row = {field: "" for field in SAMPLE_FIELDS}
        row.update(event)
        row.update({"sample_seed": seed, "sample_locked": "True", "recovery_status": "pending_archive"})
        rows.append(row)
    write_csv(SAMPLE_PATH, rows, SAMPLE_FIELDS)
    write_csv(ATTEMPTS_PATH, [], ATTEMPT_FIELDS)
    clean_ids = [row["event_id"] for row in clean]
    sample_ids = [row["event_id"] for row in rows]
    meta = {
        "design_status": "valid_window_frozen",
        "seed": seed,
        "window_start": START.isoformat(),
        "window_end": END.isoformat(),
        "source_periods": periods,
        "raw_forecast_revision_universe_count": len(raw),
        "clean_numeric_revision_intent_universe_count": len(clean),
        "excluded_dirty_event_count": len(raw) - len(clean),
        "selection_filter": (
            "title contains 業績予想の修正; excludes dividend, withdrawal, cancellation, "
            "undetermined and actual-vs-forecast difference patterns"
        ),
        "numeric_completeness_rule": (
            "Event class implies a numerical earnings-forecast revision; actual old/new field "
            "completeness is evaluated only after freeze and failures remain in the denominator."
        ),
        "clean_universe_ids_sha256": sha256_bytes(canonical_json(clean_ids).encode("utf-8")),
        "sample_size": len(rows),
        "sample_ids_sha256": sha256_bytes(canonical_json(sample_ids).encode("utf-8")),
        "sample_ids": sample_ids,
        "archive_attempts_started": False,
        "jquants_attempts_started": False,
        "outcomes_used_for_selection": [],
    }
    write_json(META_PATH, meta)
    print(json.dumps({key: value for key, value in meta.items() if key != "sample_ids"}, indent=2, sort_keys=True))


def archive_stage():
    rows = read_rows(SAMPLE_PATH)
    if len(rows) != 20 or any(row["recovery_status"] != "pending_archive" for row in rows):
        raise RuntimeError("Expected an untouched valid-window sample")
    attempts = []
    for index, row in enumerate(rows):
        direct = direct_document_attempt(row)
        direct.update({"event_id": row["event_id"], "attempt_order": 1})
        attempts.append(direct)
        attempts.append({
            "event_id": row["event_id"], "attempt_order": 2,
            "source_type": "jquants_v2_fin_summary", "source_url": "https://api.jquants.com/v2/fins/summary",
            "attempted_utc": "", "http_status": "", "content_bytes": 0,
            "result": "pending_api_key", "evidence_note": "No request made; waiting for JQUANTS_API_KEY in local .env",
        })
        archive = wayback_attempt(row)
        archive.update({"event_id": row["event_id"], "attempt_order": 3})
        attempts.append(archive)
        row["recovery_status"] = "pending_jquants"
        row["evidence_url"] = archive["source_url"] if archive["result"] == "snapshot_available" else ""
        row["failure_reason"] = (
            f"intermediate only: official={direct['result']}; wayback={archive['result']}; jquants=pending_api_key"
        )
        if index + 1 < len(rows):
            time.sleep(2)
    write_csv(SAMPLE_PATH, rows, SAMPLE_FIELDS)
    write_csv(ATTEMPTS_PATH, attempts, ATTEMPT_FIELDS)
    snapshots = sum(row["source_type"] == "wayback" and row["result"] == "snapshot_available" for row in attempts)
    summary = {
        "status": "intermediate_awaiting_jquants_api_key",
        "sample_size": len(rows),
        "complete_numeric_recoveries_without_jquants": 0,
        "complete_numeric_recovery_rate_without_jquants": 0.0,
        "wayback_snapshots_available_unparsed": snapshots,
        "jquants_requests_made": 0,
        "gate_threshold": "at least 12/20 only after official/issuer, J-Quants and Wayback stages",
        "gate_verdict": "not_evaluated",
        "no_403_bypass": True,
    }
    write_json(SUMMARY_PATH, summary)
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    meta["archive_attempts_started"] = True
    meta["archive_attempts_complete"] = True
    write_json(META_PATH, meta)
    print(json.dumps(summary, indent=2, sort_keys=True))


def jquants_stage():
    api_key = os.environ.get("JQUANTS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("JQUANTS_API_KEY is required in the local environment; no key is read from Git")
    rows = read_rows(SAMPLE_PATH)
    attempts = read_rows(ATTEMPTS_PATH)
    if len(rows) != 20 or any(row["recovery_status"] != "pending_jquants" for row in rows):
        raise RuntimeError("Expected a completed archive stage awaiting J-Quants")
    pending_by_event = {
        row["event_id"]: index for index, row in enumerate(attempts)
        if row["source_type"] == "jquants_v2_fin_summary" and row["result"] == "pending_api_key"
    }
    for index, row in enumerate(rows):
        jq, values = recover_from_jquants(row, api_key, date.today())
        jq.update({"event_id": row["event_id"], "attempt_order": 2})
        attempts[pending_by_event[row["event_id"]]] = jq
        if values:
            row.update(values)
        row["recovery_status"] = "recovered" if jq["result"] == "recovered" else "failed"
        if jq["result"] == "recovered":
            row["evidence_url"] = jq["source_url"]
            row["failure_reason"] = ""
        else:
            row["failure_reason"] = row["failure_reason"].replace("jquants=pending_api_key", f"jquants={jq['result']}")
        if index + 1 < len(rows):
            time.sleep(12.5)  # Official Free limit: 5 calls/minute.
    write_csv(SAMPLE_PATH, rows, SAMPLE_FIELDS)
    write_csv(ATTEMPTS_PATH, attempts, ATTEMPT_FIELDS)
    recovered = sum(row["recovery_status"] == "recovered" for row in rows)
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    summary.update({
        "status": "all_stages_complete",
        "complete_numeric_recoveries_all_stages": recovered,
        "complete_numeric_recovery_rate_all_stages": recovered / len(rows),
        "jquants_requests_made": len(rows),
        "gate_verdict": "pass" if recovered >= 12 else "fail",
    })
    write_json(SUMMARY_PATH, summary)
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    meta["jquants_attempts_started"] = True
    meta["jquants_attempts_complete"] = True
    write_json(META_PATH, meta)
    print(json.dumps(summary, indent=2, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("invalidate_legacy", "freeze", "archive", "jquants"))
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    if args.phase == "invalidate_legacy":
        invalidate_legacy_window()
    elif args.phase == "freeze":
        freeze(args.sample_size, args.seed)
    elif args.phase == "archive":
        archive_stage()
    else:
        jquants_stage()


if __name__ == "__main__":
    main()

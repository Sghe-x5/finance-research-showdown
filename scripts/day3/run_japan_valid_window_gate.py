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
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

import requests

DAY2 = Path(__file__).resolve().parents[1] / "day2"
DAY3 = Path(__file__).resolve().parent
sys.path.insert(0, str(DAY2))
sys.path.insert(0, str(DAY3))

from common import SEED, canonical_json, sha256_bytes, sha256_file, write_csv, write_json  # noqa: E402
from recover_japan_revisions import forecast_events  # noqa: E402
from run_japan_recovery_gate import (  # noqa: E402
    ATTEMPT_FIELDS, JQUANTS_URL, SAMPLE_FIELDS, attempt, clean_event,
    direct_document_attempt, wayback_attempt,
)


START = date(2024, 9, 1)
END = date(2026, 5, 15)
SAMPLE_PATH = Path("data/day3/japan_valid_window_sample.csv")
ATTEMPTS_PATH = Path("data/day3/japan_valid_window_attempts.csv")
META_PATH = Path("data/day3/japan_valid_window_meta.json")
SUMMARY_PATH = Path("data/day3/japan_valid_window_summary.json")
UNIVERSE_IDS_PATH = Path("data/day3/japan_valid_window_universe_ids.csv")
LEGACY_SAMPLE_PATH = Path("data/day3/japan_gate_sample.csv")
LEGACY_META_PATH = Path("data/day3/japan_gate_meta.json")
DOCTYPE_PROBE_PATH = Path("data/day3/japan_jquants_doctype_probe.json")
RAW_CACHE_DIR = Path("/private/tmp/finance-day3-jquants-cache")
JQUANTS_RATE_SECONDS = 12.5
RUN_DATE = "2026-08-14"

JQUANTS_PROVENANCE_FIELDS = [
    "prior_disclosure_timestamp_jst", "revision_disclosure_timestamp_jst",
    "old_source_record_id", "new_source_record_id", "fiscal_period_start",
    "fiscal_period_end", "forecast_horizon", "basis", "currency", "units",
    "accounting_standard", "continuing_operations_scope", "period_length_days",
    "reconstruction_rule", "recovery_confidence", "jquants_doctype",
]
VALID_SAMPLE_FIELDS = SAMPLE_FIELDS + JQUANTS_PROVENANCE_FIELDS

FORECAST_CONFIGS = [
    ("FY", "consolidated", {"revenue": "FSales", "operating_profit": "FOP", "ordinary_profit": "FOdP", "net_income": "FNP"}),
    ("FY", "standalone", {"revenue": "FNCSales", "operating_profit": "FNCOP", "ordinary_profit": "FNCOdP", "net_income": "FNCNP"}),
    ("2Q", "consolidated", {"revenue": "FSales2Q", "operating_profit": "FOP2Q", "ordinary_profit": "FOdP2Q", "net_income": "FNP2Q"}),
    ("2Q", "standalone", {"revenue": "FNCSales2Q", "operating_profit": "FNCOP2Q", "ordinary_profit": "FNCOdP2Q", "net_income": "FNCNP2Q"}),
]


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def migrate_schema_and_metadata():
    """Apply a provenance-only schema correction without touching the frozen IDs."""
    rows = read_rows(SAMPLE_PATH)
    write_csv(SAMPLE_PATH, rows, VALID_SAMPLE_FIELDS)
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    meta.update({
        "run_date": RUN_DATE,
        "jquants_plan_expected": "Free",
        "jquants_plan_resolved": "pending_api_execution",
        "jquants_api_version": "v2",
        "jquants_endpoint": JQUANTS_URL,
        "jquants_advertised_history_length": "2 years",
        "jquants_advertised_delay": "12 weeks",
        "resolved_available_from_date": START.isoformat(),
        "resolved_available_to_date": END.isoformat(),
        "actual_api_min_date": None,
        "actual_api_max_date": None,
        "fixed_window_expansion_after_results_allowed": False,
        "selection_uses_recovery_success": False,
        "failed_rows_replaceable": False,
        "raw_jquants_storage": str(RAW_CACHE_DIR) + " (outside Git)",
        "distribution_status": "private research only; redistribution rights not established",
        "doctype_probe_required_before_reconstruction": True,
        "issuer_ir_attempts_started": False,
    })
    write_json(META_PATH, meta)
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    summary.update({
        "status": "Japan gate pending J-Quants execution; 0/20 recovered through issuer/archives only.",
        "status_code": "pending_jquants_execution",
        "gate_verdict": "not_evaluated",
        "issuer_ir_requests_made": 0,
        "distribution_status": "private research only",
    })
    summary.pop("gate_threshold", None)
    write_json(SUMMARY_PATH, summary)


def materialize_universe_ids():
    """Commit only eligible IDs, verifying the original pre-recovery universe hash."""
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    raw = sorted(forecast_events(monthly_periods()), key=lambda row: row["event_id"])
    clean_ids = [row["event_id"] for row in raw if clean_event(row)]
    digest = sha256_bytes(canonical_json(clean_ids).encode("utf-8"))
    if digest != meta["clean_universe_ids_sha256"]:
        raise RuntimeError(
            "Re-materialized eligible universe differs from the frozen hash: "
            f"expected={meta['clean_universe_ids_sha256']} actual={digest}"
        )
    write_csv(UNIVERSE_IDS_PATH, [{"event_id": event_id} for event_id in clean_ids], ["event_id"])
    meta.update({
        "eligible_universe_ids_file": str(UNIVERSE_IDS_PATH),
        "eligible_universe_ids_file_sha256": sha256_file(UNIVERSE_IDS_PATH),
        "eligible_universe_ids_count": len(clean_ids),
        "eligible_universe_materialized_after_freeze_by_hash_verification": True,
    })
    write_json(META_PATH, meta)
    print(json.dumps({
        "eligible_universe_ids_count": len(clean_ids),
        "clean_universe_ids_sha256": digest,
        "eligible_universe_ids_file_sha256": meta["eligible_universe_ids_file_sha256"],
        "sample_ids_unchanged": meta["sample_ids"],
    }, indent=2, sort_keys=True))


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
        row = {field: "" for field in VALID_SAMPLE_FIELDS}
        row.update(event)
        row.update({"sample_seed": seed, "sample_locked": "True", "recovery_status": "pending_archive"})
        rows.append(row)
    write_csv(SAMPLE_PATH, rows, VALID_SAMPLE_FIELDS)
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
        "selection_uses_recovery_success": False,
        "failed_rows_replaceable": False,
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
    write_csv(SAMPLE_PATH, rows, VALID_SAMPLE_FIELDS)
    write_csv(ATTEMPTS_PATH, attempts, ATTEMPT_FIELDS)
    snapshots = sum(row["source_type"] == "wayback" and row["result"] == "snapshot_available" for row in attempts)
    summary = {
        "status": "Japan gate pending J-Quants execution; 0/20 recovered through issuer/archives only.",
        "status_code": "pending_jquants_execution",
        "sample_size": len(rows),
        "complete_numeric_recoveries_without_jquants": 0,
        "complete_numeric_recovery_rate_without_jquants": 0.0,
        "wayback_snapshots_available_unparsed": snapshots,
        "jquants_requests_made": 0,
        "gate_verdict": "not_evaluated",
        "issuer_ir_requests_made": 0,
        "distribution_status": "private research only",
        "no_403_bypass": True,
    }
    write_json(SUMMARY_PATH, summary)
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    meta["archive_attempts_started"] = True
    meta["archive_attempts_complete"] = True
    write_json(META_PATH, meta)
    print(json.dumps(summary, indent=2, sort_keys=True))


def normalized_date(value):
    digits = "".join(character for character in str(value or "") if character.isdigit())
    if len(digits) < 8:
        return ""
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"


def normalized_time(value):
    digits = "".join(character for character in str(value or "") if character.isdigit())
    if len(digits) < 4:
        return "00:00:00"
    seconds = digits[4:6] if len(digits) >= 6 else "00"
    return f"{digits[:2]}:{digits[2:4]}:{seconds}"


def disclosure_timestamp(record):
    return f"{normalized_date(record.get('DiscDate'))} {normalized_time(record.get('DiscTime'))}"


def request_jquants_page(api_key, params, max_retries=6):
    for retry in range(max_retries):
        response = requests.get(JQUANTS_URL, params=params, headers={"x-api-key": api_key}, timeout=60)
        if response.status_code != 429:
            response.raise_for_status()
            return response.json()
        retry_after = response.headers.get("Retry-After", "")
        try:
            wait_seconds = float(retry_after)
        except ValueError:
            wait_seconds = min(120.0, 5.0 * (2 ** retry))
        time.sleep(max(JQUANTS_RATE_SECONDS, wait_seconds))
    raise RuntimeError("J-Quants returned HTTP 429 after bounded exponential backoff")


def fetch_jquants_rows(api_key, code):
    """Fetch every page, fail on schema/token cycles, cache raw pages outside Git."""
    pages = []
    rows = []
    pagination_key = ""
    seen_keys = set()
    while True:
        params = {"code": f"{code}0"}
        if pagination_key:
            params["pagination_key"] = pagination_key
        payload = request_jquants_page(api_key, params)
        if not isinstance(payload.get("data", []), list):
            raise RuntimeError("Unexpected J-Quants schema: data is not a list")
        page_rows = payload.get("data", [])
        for record in page_rows:
            missing = {field for field in ("DiscDate", "Code", "DiscNo", "DocType") if field not in record}
            if missing:
                raise RuntimeError(f"Unexpected J-Quants summary schema; missing={sorted(missing)}")
        pages.append(payload)
        rows.extend(page_rows)
        next_key = payload.get("pagination_key") or ""
        if not next_key:
            break
        if next_key in seen_keys:
            raise RuntimeError("J-Quants pagination key repeated; refusing a partial silent result")
        seen_keys.add(next_key)
        pagination_key = next_key
        time.sleep(JQUANTS_RATE_SECONDS)
    RAW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_CACHE_DIR / f"fin_summary_{code}.json"
    raw_path.write_text(canonical_json(pages), encoding="utf-8")
    dates = sorted(filter(None, (normalized_date(record.get("DiscDate")) for record in rows)))
    return rows, {
        "code": code,
        "page_count": len(pages),
        "row_count": len(rows),
        "raw_cache_sha256": sha256_file(raw_path),
        "actual_min_date": dates[0] if dates else None,
        "actual_max_date": dates[-1] if dates else None,
    }


def doctype_probe(event_id=""):
    api_key = os.environ.get("JQUANTS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("JQUANTS_API_KEY is required for the DocType probe")
    rows = read_rows(SAMPLE_PATH)
    event = next((row for row in rows if row["event_id"] == event_id), rows[0] if not event_id else None)
    if event is None:
        raise RuntimeError(f"Unknown frozen event ID for probe: {event_id}")
    api_rows, fetch_meta = fetch_jquants_rows(api_key, event["security_code"])
    distribution = Counter(str(row.get("DocType", "")) for row in api_rows)
    examples = {}
    for record in api_rows:
        doc_type = str(record.get("DocType", ""))
        examples.setdefault(doc_type, [])
        if len(examples[doc_type]) < 3:
            examples[doc_type].append({
                "record_id": record.get("DiscNo", ""),
                "timestamp_jst": disclosure_timestamp(record),
            })
    output = {
        "probe_event_id": event["event_id"],
        "security_code": event["security_code"],
        "event_timestamp_jst": event["publication_timestamp_jst"],
        "doctype_distribution": dict(sorted(distribution.items())),
        "doctype_examples": dict(sorted(examples.items())),
        "fetch_provenance": fetch_meta,
        "review_status": "pending_human_review",
        "approved_revision_doc_types": [],
        "note": "No recovery was attempted. Approve document types only after reviewing this distribution.",
    }
    write_json(DOCTYPE_PROBE_PATH, output)
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    meta["jquants_plan_resolved"] = os.environ.get("JQUANTS_PLAN", "Free")
    meta["doctype_probe_actual_api_min_date"] = fetch_meta["actual_min_date"]
    meta["doctype_probe_actual_api_max_date"] = fetch_meta["actual_max_date"]
    meta["doctype_probe_status"] = "pending_human_review"
    write_json(META_PATH, meta)
    print(json.dumps(output, indent=2, sort_keys=True))


def period_length_days(record):
    start = normalized_date(record.get("CurFYSt"))
    end = normalized_date(record.get("CurFYEn"))
    if not start or not end:
        return None
    return (date.fromisoformat(end) - date.fromisoformat(start)).days + 1


def forecast_payload(record):
    for horizon, basis, fields in FORECAST_CONFIGS:
        values = {metric: record.get(field, "") for metric, field in fields.items()}
        if any(value not in (None, "") for value in values.values()):
            start = normalized_date(record.get("CurFYSt"))
            end = normalized_date(record.get("CurFYEn"))
            return {
                "horizon": horizon,
                "basis": basis,
                "values": values,
                "fiscal_start": start,
                "fiscal_end": end,
                "period_length_days": period_length_days(record),
                "currency": "JPY",
                "units": "JPY (J-Quants normalized numeric field)",
                "accounting_standard": "not_exposed_by_v2_fin_summary",
                "continuing_operations_scope": "not_exposed_by_v2_fin_summary",
                "signature": (horizon, basis, start, end, period_length_days(record)),
            }
    return None


def reconstruct_forecast_pair(event, api_rows, approved_revision_doc_types):
    event_date = event["publication_timestamp_jst"][:10]
    event_time = event["publication_timestamp_jst"][11:16]
    current_options = [
        row for row in api_rows
        if str(row.get("DocType", "")) in approved_revision_doc_types
        and normalized_date(row.get("DiscDate")) == event_date
        and normalized_time(row.get("DiscTime"))[:5] == event_time
    ]
    if not current_options:
        return "revision_record_not_found", {}, "No approved revision DocType at the exact event timestamp"
    if len(current_options) != 1:
        return "ambiguous_revision_record", {}, f"Exact timestamp matched {len(current_options)} approved revision records"
    current = current_options[0]
    current_payload = forecast_payload(current)
    if current_payload is None or not all(value not in (None, "") for value in current_payload["values"].values()):
        return "incomplete_new_forecast", {}, "Revision record lacks a complete four-metric forecast on one basis/horizon"
    current_ts = disclosure_timestamp(current)
    prior_candidates = []
    for record in api_rows:
        if disclosure_timestamp(record) >= current_ts:
            continue
        payload = forecast_payload(record)
        if payload and payload["signature"] == current_payload["signature"]:
            prior_candidates.append((disclosure_timestamp(record), record, payload))
    if not prior_candidates:
        fiscal_start = current_payload["fiscal_start"]
        if fiscal_start and fiscal_start < START.isoformat():
            return "prior_outside_window", {}, "Matching fiscal year started before the conservative available-from date"
        return "ambiguous_old_forecast", {}, "No unambiguous prior record with the same period, horizon and basis"
    latest_timestamp = max(item[0] for item in prior_candidates)
    latest = [item for item in prior_candidates if item[0] == latest_timestamp]
    value_signatures = {canonical_json(item[2]["values"]) for item in latest}
    if len(value_signatures) != 1:
        return "ambiguous_old_forecast", {}, "Latest compatible timestamp contains conflicting forecast values"
    _, prior, prior_payload = sorted(latest, key=lambda item: str(item[1].get("DiscNo", "")))[-1]
    if not all(value not in (None, "") for value in prior_payload["values"].values()):
        return "ambiguous_old_forecast", {}, "Latest compatible prior record has incomplete old values"
    values = {
        "old_revenue": str(prior_payload["values"]["revenue"]),
        "new_revenue": str(current_payload["values"]["revenue"]),
        "old_operating_profit": str(prior_payload["values"]["operating_profit"]),
        "new_operating_profit": str(current_payload["values"]["operating_profit"]),
        "old_ordinary_profit": str(prior_payload["values"]["ordinary_profit"]),
        "new_ordinary_profit": str(current_payload["values"]["ordinary_profit"]),
        "old_net_income": str(prior_payload["values"]["net_income"]),
        "new_net_income": str(current_payload["values"]["net_income"]),
        "prior_disclosure_timestamp_jst": disclosure_timestamp(prior),
        "revision_disclosure_timestamp_jst": current_ts,
        "old_source_record_id": str(prior.get("DiscNo", "")),
        "new_source_record_id": str(current.get("DiscNo", "")),
        "fiscal_period_start": current_payload["fiscal_start"],
        "fiscal_period_end": current_payload["fiscal_end"],
        "forecast_horizon": current_payload["horizon"],
        "basis": current_payload["basis"],
        "currency": current_payload["currency"],
        "units": current_payload["units"],
        "accounting_standard": current_payload["accounting_standard"],
        "continuing_operations_scope": current_payload["continuing_operations_scope"],
        "period_length_days": current_payload["period_length_days"],
        "reconstruction_rule": "latest public compatible forecast before exact approved revision record",
        "recovery_confidence": "medium_strict_fields; accounting standard and continuing-ops scope not exposed",
        "jquants_doctype": str(current.get("DocType", "")),
    }
    return "recovered", values, f"old={prior.get('DiscNo', '')}; new={current.get('DiscNo', '')}"


def jquants_stage():
    api_key = os.environ.get("JQUANTS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("JQUANTS_API_KEY is required in the local environment; no key is read from Git")
    if not DOCTYPE_PROBE_PATH.exists():
        raise RuntimeError("Run probe_doctype and show its distribution before any reconstruction")
    probe = json.loads(DOCTYPE_PROBE_PATH.read_text(encoding="utf-8"))
    if probe.get("review_status") != "approved" or not probe.get("approved_revision_doc_types"):
        raise RuntimeError("DocType distribution requires human approval before reconstruction")
    rows = read_rows(SAMPLE_PATH)
    attempts = read_rows(ATTEMPTS_PATH)
    if len(rows) != 20 or any(row["recovery_status"] != "pending_jquants" for row in rows):
        raise RuntimeError("Expected a completed archive stage awaiting J-Quants")
    pending_by_event = {
        row["event_id"]: index for index, row in enumerate(attempts)
        if row["source_type"] == "jquants_v2_fin_summary" and row["result"] == "pending_api_key"
    }
    fetch_manifest = []
    actual_dates = []
    for index, row in enumerate(rows):
        try:
            api_rows, fetch_meta = fetch_jquants_rows(api_key, row["security_code"])
            fetch_manifest.append(fetch_meta)
            actual_dates.extend(filter(None, (fetch_meta["actual_min_date"], fetch_meta["actual_max_date"])))
            result, values, note = reconstruct_forecast_pair(
                row, api_rows, set(probe["approved_revision_doc_types"]),
            )
            jq = attempt("jquants_v2_fin_summary", JQUANTS_URL, result, note)
        except (requests.RequestException, RuntimeError, ValueError) as exc:
            values = {}
            jq = attempt("jquants_v2_fin_summary", JQUANTS_URL, "request_or_schema_error", str(exc)[:240])
        jq.update({"event_id": row["event_id"], "attempt_order": 2})
        attempts[pending_by_event[row["event_id"]]] = jq
        if values:
            row.update(values)
        row["recovery_status"] = jq["result"]
        if jq["result"] == "recovered":
            row["evidence_url"] = jq["source_url"]
            row["failure_reason"] = ""
        else:
            row["failure_reason"] = row["failure_reason"].replace("jquants=pending_api_key", f"jquants={jq['result']}")
        if index + 1 < len(rows):
            time.sleep(12.5)  # Official Free limit: 5 calls/minute.
    write_csv(SAMPLE_PATH, rows, VALID_SAMPLE_FIELDS)
    write_csv(ATTEMPTS_PATH, attempts, ATTEMPT_FIELDS)
    result_counts = Counter(row["recovery_status"] for row in rows)
    recovered = result_counts["recovered"]
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    summary.update({
        "status": f"Japan gate pending issuer IR execution; {recovered}/20 recovered after J-Quants and archives.",
        "status_code": "pending_issuer_ir_execution",
        "jquants_recovery_status_counts": dict(sorted(result_counts.items())),
        "jquants_requests_made": len(rows),
        "gate_verdict": "not_evaluated",
    })
    write_json(SUMMARY_PATH, summary)
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    meta["jquants_attempts_started"] = True
    meta["jquants_attempts_complete"] = True
    meta["jquants_plan_resolved"] = os.environ.get("JQUANTS_PLAN", "Free")
    meta["actual_api_min_date"] = min(actual_dates) if actual_dates else None
    meta["actual_api_max_date"] = max(actual_dates) if actual_dates else None
    meta["raw_cache_hash_manifest"] = fetch_manifest
    write_json(META_PATH, meta)
    print(json.dumps(summary, indent=2, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "phase",
        choices=(
            "invalidate_legacy", "freeze", "archive", "migrate_schema",
            "materialize_universe_ids", "probe_doctype", "jquants",
        ),
    )
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--event-id", default="")
    args = parser.parse_args()
    if args.phase == "invalidate_legacy":
        invalidate_legacy_window()
    elif args.phase == "freeze":
        freeze(args.sample_size, args.seed)
    elif args.phase == "archive":
        archive_stage()
    elif args.phase == "migrate_schema":
        migrate_schema_and_metadata()
    elif args.phase == "materialize_universe_ids":
        materialize_universe_ids()
    elif args.phase == "probe_doctype":
        doctype_probe(args.event_id)
    else:
        jquants_stage()


if __name__ == "__main__":
    main()

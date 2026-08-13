#!/usr/bin/env python3
"""Freeze and run the bounded 20-event Japan numeric-recovery gate."""

import argparse
import csv
import json
import os
import random
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import requests

DAY2 = Path(__file__).resolve().parents[1] / "day2"
sys.path.insert(0, str(DAY2))

from common import SEED, canonical_json, sha256_bytes, write_csv, write_json  # noqa: E402
from recover_japan_revisions import PERIODS, forecast_events  # noqa: E402


SAMPLE_PATH = Path("data/day3/japan_gate_sample.csv")
ATTEMPTS_PATH = Path("data/day3/japan_gate_attempts.csv")
META_PATH = Path("data/day3/japan_gate_meta.json")
SUMMARY_PATH = Path("data/day3/japan_gate_summary.json")
JQUANTS_URL = "https://api.jquants.com/v2/fins/summary"
JQUANTS_POLICY_URL = "https://jpx-jquants.com/en/"
WAYBACK_URL = "https://archive.org/wayback/available"

EXCLUDE_TITLE_PATTERNS = (
    "配当", "撤回", "取下げ", "取り下げ", "中止", "未定",
    "実績値との差異", "予想と実績", "実績との差異", "差異に関する",
)

SAMPLE_FIELDS = [
    "event_id", "security_code", "issuer", "publication_timestamp_jst", "title_jp",
    "yanoshin_id", "yanoshin_document_url", "sample_seed", "sample_locked",
    "recovery_status", "old_revenue", "new_revenue", "old_operating_profit",
    "new_operating_profit", "old_ordinary_profit", "new_ordinary_profit",
    "old_net_income", "new_net_income", "evidence_url", "failure_reason",
]

ATTEMPT_FIELDS = [
    "event_id", "attempt_order", "source_type", "source_url", "attempted_utc",
    "http_status", "content_bytes", "result", "evidence_note",
]

FORECAST_FIELDS = {
    "revenue": "FSales", "operating_profit": "FOP",
    "ordinary_profit": "FOdP", "net_income": "FNP",
}


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean_event(event):
    title = event.get("title_jp", "")
    return "業績予想の修正" in title and not any(pattern in title for pattern in EXCLUDE_TITLE_PATTERNS)


def freeze(sample_size=20, seed=SEED):
    if SAMPLE_PATH.exists() or ATTEMPTS_PATH.exists():
        raise RuntimeError("Refusing to overwrite an existing Japan gate sample or attempt log")
    universe = sorted(forecast_events(PERIODS), key=lambda row: row["event_id"])
    filtered = [row for row in universe if clean_event(row)]
    if len(filtered) < sample_size:
        raise RuntimeError(f"Need {sample_size} clean events, found {len(filtered)}")
    selected = sorted(random.Random(seed).sample(filtered, sample_size), key=lambda row: row["event_id"])
    rows = []
    for event in selected:
        row = {field: "" for field in SAMPLE_FIELDS}
        row.update(event)
        row.update({
            "sample_seed": seed, "sample_locked": "True", "recovery_status": "pending",
        })
        rows.append(row)
    write_csv(SAMPLE_PATH, rows, SAMPLE_FIELDS)
    write_csv(ATTEMPTS_PATH, [], ATTEMPT_FIELDS)
    universe_ids = [row["event_id"] for row in universe]
    filtered_ids = [row["event_id"] for row in filtered]
    selected_ids = [row["event_id"] for row in rows]
    meta = {
        "seed": seed,
        "source_periods": PERIODS,
        "raw_forecast_revision_universe_count": len(universe),
        "clean_event_universe_count": len(filtered),
        "excluded_dirty_event_count": len(universe) - len(filtered),
        "excluded_title_patterns": list(EXCLUDE_TITLE_PATTERNS),
        "raw_universe_ids_sha256": sha256_bytes(canonical_json(universe_ids).encode("utf-8")),
        "clean_universe_ids_sha256": sha256_bytes(canonical_json(filtered_ids).encode("utf-8")),
        "sample_size": len(rows),
        "sample_ids_sha256": sha256_bytes(canonical_json(selected_ids).encode("utf-8")),
        "sample_ids": selected_ids,
        "recovery_started": False,
        "outcomes_used_for_selection": [],
    }
    write_json(META_PATH, meta)
    print(json.dumps({key: value for key, value in meta.items() if key != "sample_ids"}, indent=2, sort_keys=True))


def attempt(source_type, source_url, result, note, status="", size=0):
    return {
        "source_type": source_type, "source_url": source_url, "attempted_utc": utc_now(),
        "http_status": status, "content_bytes": size, "result": result,
        "evidence_note": note,
    }


def direct_document_attempt(row):
    url = row["yanoshin_document_url"]
    if not url:
        return attempt("official_tdnet_document", "", "missing_url", "Historical index supplied no document URL")
    try:
        response = requests.get(url, timeout=45, allow_redirects=True)
        size = len(response.content)
        alive = response.status_code == 200 and size > 500
        return attempt(
            "official_tdnet_document", url, "alive" if alive else "dead",
            f"final_url={response.url}; alive requires HTTP 200 and >500 bytes",
            response.status_code, size,
        )
    except requests.RequestException as exc:
        return attempt("official_tdnet_document", url, "request_error", str(exc)[:240])


def parse_event_date(row):
    return date.fromisoformat(row["publication_timestamp_jst"][:10])


def jquants_free_eligibility(row, today):
    cutoff = today - timedelta(days=365 * 2)
    return parse_event_date(row) >= cutoff, cutoff.isoformat()


def jquants_rows(api_key, code):
    response = requests.get(
        JQUANTS_URL, params={"code": f"{code}0"}, headers={"x-api-key": api_key}, timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    rows = list(payload.get("data", []))
    while payload.get("pagination_key"):
        response = requests.get(
            JQUANTS_URL,
            params={"code": f"{code}0", "pagination_key": payload["pagination_key"]},
            headers={"x-api-key": api_key}, timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        rows.extend(payload.get("data", []))
    return rows


def same_fiscal_period(left, right):
    return left.get("CurFYEn") and left.get("CurFYEn") == right.get("CurFYEn")


def numeric(value):
    if value in (None, ""):
        return ""
    return str(value)


def recover_from_jquants(row, api_key, today):
    eligible, cutoff = jquants_free_eligibility(row, today)
    if not api_key:
        result = "ineligible_free_plan_history" if not eligible else "blocked_missing_api_key"
        note = (
            f"Official Free plan exposes two years of history; rolling cutoff={cutoff}. "
            "New accounts use V2 x-api-key authentication."
        )
        return attempt("jquants_v2_fin_summary", JQUANTS_URL, result, note), None
    try:
        rows = jquants_rows(api_key, row["security_code"])
    except requests.RequestException as exc:
        status = getattr(exc.response, "status_code", "") if getattr(exc, "response", None) else ""
        return attempt("jquants_v2_fin_summary", JQUANTS_URL, "request_error", str(exc)[:240], status), None
    event_date = parse_event_date(row).isoformat()
    revisions = sorted(
        [item for item in rows if str(item.get("DiscDate", ""))[:10] <= event_date],
        key=lambda item: (str(item.get("DiscDate", "")), str(item.get("DiscTime", ""))),
    )
    current_options = [item for item in revisions if str(item.get("DiscDate", ""))[:10] == event_date and "ForecastRevision" in str(item.get("DocType", ""))]
    if not current_options:
        return attempt("jquants_v2_fin_summary", JQUANTS_URL, "event_not_found", f"rows_for_code={len(rows)}"), None
    current = current_options[-1]
    prior_options = [item for item in revisions if item is not current and same_fiscal_period(item, current)]
    if not prior_options:
        return attempt("jquants_v2_fin_summary", JQUANTS_URL, "prior_forecast_not_found", "New forecast found but old forecast was unavailable"), None
    prior = prior_options[-1]
    values = {}
    for label, field in FORECAST_FIELDS.items():
        values[f"old_{label}"] = numeric(prior.get(field))
        values[f"new_{label}"] = numeric(current.get(field))
    complete = all(values.values())
    result = "recovered" if complete else "partial_numeric_recovery"
    return attempt("jquants_v2_fin_summary", JQUANTS_URL, result, f"matched DiscNo={current.get('DiscNo', '')}; prior DiscNo={prior.get('DiscNo', '')}"), values


def wayback_attempt(row):
    target = row["yanoshin_document_url"]
    if not target:
        return attempt("wayback", "", "missing_target_url", "No historical document URL to query")
    timestamp = re.sub(r"\D", "", row["publication_timestamp_jst"])[:14]
    url = f"{WAYBACK_URL}?url={quote(target, safe='')}&timestamp={timestamp}"
    try:
        response = requests.get(WAYBACK_URL, params={"url": target, "timestamp": timestamp}, timeout=45)
        response.raise_for_status()
        closest = response.json().get("archived_snapshots", {}).get("closest", {})
        available = closest.get("available") is True and closest.get("status") == "200"
        snapshot = closest.get("url", "")
        return attempt(
            "wayback", snapshot or url, "snapshot_available" if available else "no_snapshot",
            f"closest_timestamp={closest.get('timestamp', '')}; target={target}", response.status_code,
            len(response.content),
        )
    except (requests.RequestException, ValueError) as exc:
        status = getattr(exc.response, "status_code", "") if getattr(exc, "response", None) else ""
        return attempt("wayback", url, "request_error", str(exc)[:240], status)


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def recover(today=None):
    today = today or date.today()
    rows = read_rows(SAMPLE_PATH)
    if len(rows) != 20 or any(row["sample_locked"] != "True" for row in rows):
        raise RuntimeError("Expected the locked 20-event Japan gate sample")
    if any(row["recovery_status"] != "pending" for row in rows):
        raise RuntimeError("Refusing to rerun or overwrite recovery outcomes")
    api_key = os.environ.get("JQUANTS_API_KEY", "").strip()
    attempts = []
    for index, row in enumerate(rows):
        direct = direct_document_attempt(row)
        direct.update({"event_id": row["event_id"], "attempt_order": 1})
        attempts.append(direct)
        jq, values = recover_from_jquants(row, api_key, today)
        jq.update({"event_id": row["event_id"], "attempt_order": 2})
        attempts.append(jq)
        if values:
            row.update(values)
        archive = wayback_attempt(row)
        archive.update({"event_id": row["event_id"], "attempt_order": 3})
        attempts.append(archive)
        if jq["result"] == "recovered":
            row["recovery_status"] = "recovered"
            row["evidence_url"] = JQUANTS_URL
        elif jq["result"] == "partial_numeric_recovery":
            row["recovery_status"] = "partial"
            row["evidence_url"] = JQUANTS_URL
        else:
            row["recovery_status"] = "failed"
            row["evidence_url"] = archive["source_url"] if archive["result"] == "snapshot_available" else ""
            row["failure_reason"] = f"official={direct['result']}; jquants={jq['result']}; wayback={archive['result']}"
        if index + 1 < len(rows):
            time.sleep(2)
    write_csv(SAMPLE_PATH, rows, SAMPLE_FIELDS)
    write_csv(ATTEMPTS_PATH, attempts, ATTEMPT_FIELDS)
    counts = {status: sum(row["recovery_status"] == status for row in rows) for status in ("recovered", "partial", "failed")}
    free_eligible = sum(jquants_free_eligibility(row, today)[0] for row in rows)
    summary = {
        "as_of_date": today.isoformat(),
        "sample_size": len(rows),
        "recovery_counts": counts,
        "complete_recovery_rate": counts["recovered"] / len(rows),
        "jquants_api_version": "v2",
        "jquants_endpoint": JQUANTS_URL,
        "jquants_authentication": "JQUANTS_API_KEY environment variable / x-api-key header",
        "jquants_free_plan_policy_url": JQUANTS_POLICY_URL,
        "jquants_free_plan_history": "2 years, 12 weeks delayed",
        "sample_events_inside_free_history_window": free_eligible,
        "jquants_api_key_present": bool(api_key),
        "wayback_attempted": len(rows),
        "wayback_snapshots_available": sum(a["source_type"] == "wayback" and a["result"] == "snapshot_available" for a in attempts),
        "gate_threshold": "at least 12/20 complete old/new numeric recoveries",
        "gate_passed": counts["recovered"] >= 12,
        "no_403_bypass": True,
    }
    write_json(SUMMARY_PATH, summary)
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    meta["recovery_started"] = True
    meta["summary_sha256"] = sha256_bytes(canonical_json(summary).encode("utf-8"))
    write_json(META_PATH, meta)
    print(json.dumps(summary, indent=2, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("freeze", "recover"))
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    if args.phase == "freeze":
        freeze(args.sample_size, args.seed)
    else:
        recover()


if __name__ == "__main__":
    main()

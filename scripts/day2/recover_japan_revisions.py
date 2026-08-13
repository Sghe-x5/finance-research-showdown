#!/usr/bin/env python3
"""Freeze a Japan revision sample, then record recovery attempts without replacement."""

import argparse
import csv
import json
import random
import re
import time
from datetime import datetime
from pathlib import Path

import requests

from common import SEED, canonical_json, read_csv, sha256_bytes, stable_id, write_csv, write_json


BASE = "https://webapi.yanoshin.jp/webapi/tdnet/list/{period}.json?limit=10000"
PERIODS = ["20230110-20230131", "20230701-20230731", "20240110-20240131", "20240701-20240731"]
SAMPLE_OUTPUT = Path("data/day2/japan_revision_sample.csv")
ATTEMPTS_OUTPUT = Path("data/day2/japan_recovery_attempts.csv")
META_OUTPUT = Path("data/day2/japan_revision_sample_meta.json")
SEED_INPUT = Path("data/day2/japan_numeric_recovery_seed.csv")

SAMPLE_FIELDS = [
    "event_id", "security_code", "issuer", "fiscal_period", "publication_timestamp_jst",
    "title_jp", "old_revenue", "new_revenue", "old_operating_profit", "new_operating_profit",
    "old_ordinary_profit", "new_ordinary_profit", "old_net_income", "new_net_income",
    "revenue_change_pct", "operating_change_pct", "ordinary_change_pct", "net_change_pct",
    "direction", "recovery_status", "source_type", "evidence_url", "failure_reason",
    "period_length", "consolidation_scope", "fiscal_year_change", "units",
    "market_segment_at_event", "jp_document_timestamp", "english_document_status",
    "english_timestamp", "english_lag_minutes", "prior_bilingual_behavior",
    "foreign_ownership_pct", "treatment_status", "sample_seed", "sample_locked",
    "seed_fixture", "seed_validation_status", "yanoshin_id", "yanoshin_document_url",
]
ATTEMPT_FIELDS = [
    "event_id", "attempt_order", "source_type", "source_url", "attempted_utc",
    "http_status", "content_bytes", "result", "evidence_note",
]


def fetch_json(url):
    response = requests.get(url, timeout=90)
    response.raise_for_status()
    return response.json()


def forecast_events(periods=PERIODS):
    events = []
    for index, period in enumerate(periods):
        payload = fetch_json(BASE.format(period=period))
        for wrapped in payload.get("items", []):
            item = wrapped.get("Tdnet") or wrapped.get("TDnet") or wrapped
            title = item.get("title") or ""
            if "業績予想の修正" not in title or "配当予想" in title:
                continue
            code = re.sub(r"\D", "", item.get("company_code") or "")[:4]
            if len(code) != 4:
                continue
            event_id = f"JP_Y{item.get('id') or stable_id(code, item.get('pubdate'), title, length=12)}"
            events.append({
                "event_id": event_id,
                "security_code": code,
                "issuer": item.get("company_name") or "",
                "publication_timestamp_jst": item.get("pubdate") or "",
                "title_jp": title,
                "yanoshin_id": item.get("id") or "",
                "yanoshin_document_url": item.get("document_url") or "",
            })
        if index + 1 < len(periods):
            time.sleep(2)
    return events


def blank_sample_row(event, seed_fixture=False):
    row = {field: "" for field in SAMPLE_FIELDS}
    row.update(event)
    row.update({
        "recovery_status": "pending",
        "sample_seed": SEED,
        "sample_locked": "True",
        "seed_fixture": str(seed_fixture),
        "seed_validation_status": "pending" if seed_fixture else "not_applicable",
        "treatment_status": "pending",
    })
    return row


def freeze_sample(sample_size=40):
    seed_rows = read_csv(SEED_INPUT)
    locked = []
    for seed in seed_rows:
        locked.append(blank_sample_row({
            "event_id": seed["event_id"],
            "security_code": seed["code"],
            "issuer": seed["company"],
            "publication_timestamp_jst": seed["timestamp_jst"],
            "title_jp": "業績予想の修正 (supplied fixed seed)",
        }, seed_fixture=True))

    universe = forecast_events()
    seed_ids = {row["event_id"] for row in locked}
    universe = [row for row in universe if row["event_id"] not in seed_ids]
    universe.sort(key=lambda row: row["event_id"])
    rng = random.Random(SEED)
    selected = rng.sample(universe, sample_size - len(locked))
    locked.extend(blank_sample_row(row) for row in selected)
    locked.sort(key=lambda row: row["event_id"])
    write_csv(SAMPLE_OUTPUT, locked, SAMPLE_FIELDS)
    write_csv(ATTEMPTS_OUTPUT, [], ATTEMPT_FIELDS)
    ids = [row["event_id"] for row in locked]
    ids_sha = sha256_bytes(canonical_json({"seed": SEED, "event_ids": ids}).encode("utf-8"))
    write_json(META_OUTPUT, {
        "seed": SEED,
        "sample_size": len(locked),
        "seed_fixture_count": len(seed_rows),
        "random_universe_count": len(universe),
        "locked_event_ids_sha256": ids_sha,
        "recovery_attempts_started": False,
        "event_ids": ids,
    })
    print(json.dumps({"sample_size": len(locked), "universe": len(universe), "ids_sha256": ids_sha}, indent=2))


def pct_change(old, new):
    if old in (None, "", 0, 0.0):
        return ""
    return f"{(float(new) / float(old) - 1):.8f}"


def revision_direction(row):
    changes = []
    for old_key, new_key in (
        ("old_revenue", "new_revenue"), ("old_operating_profit", "new_operating_profit"),
        ("old_ordinary_profit", "new_ordinary_profit"), ("old_net_income", "new_net_income"),
    ):
        if row[old_key] != "" and row[new_key] != "":
            changes.append(float(row[new_key]) - float(row[old_key]))
    if changes and all(value >= 0 for value in changes) and any(value > 0 for value in changes):
        return "upward"
    if changes and all(value <= 0 for value in changes) and any(value < 0 for value in changes):
        return "downward"
    return "mixed_or_unchanged"


def merge_seed_values(rows):
    seed_by_id = {row["event_id"]: row for row in read_csv(SEED_INPUT)}
    mapping = {
        "old_revenue": "old_revenue", "new_revenue": "new_revenue",
        "old_operating_profit": "old_operating", "new_operating_profit": "new_operating",
        "old_ordinary_profit": "old_ordinary", "new_ordinary_profit": "new_ordinary",
        "old_net_income": "old_net", "new_net_income": "new_net",
    }
    for row in rows:
        seed = seed_by_id.get(row["event_id"])
        if not seed:
            continue
        for target, source in mapping.items():
            row[target] = seed[source]
        row["revenue_change_pct"] = pct_change(row["old_revenue"], row["new_revenue"])
        row["operating_change_pct"] = pct_change(row["old_operating_profit"], row["new_operating_profit"])
        row["ordinary_change_pct"] = pct_change(row["old_ordinary_profit"], row["new_ordinary_profit"])
        row["net_change_pct"] = pct_change(row["old_net_income"], row["new_net_income"])
        row["direction"] = revision_direction(row)
        row["recovery_status"] = "recovered_provisional"
        row["source_type"] = seed["source_type"]
        row["evidence_url"] = seed["source_url"]
        row["seed_validation_status"] = "blocked_http_403_flagged_not_silently_corrected"
        row["failure_reason"] = "IRBank rejected automated validation with HTTP 403; supplied values retained as provisional fixtures"
        row["treatment_status"] = "incomplete"


def attempt_official(row, order):
    url = row["yanoshin_document_url"]
    attempted = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    if not url:
        return {
            "event_id": row["event_id"], "attempt_order": order, "source_type": "issuer_or_tdnet_pdf",
            "source_url": "", "attempted_utc": attempted, "http_status": "", "content_bytes": 0,
            "result": "missing_url", "evidence_note": "Yanoshin index has no document URL",
        }
    try:
        response = requests.get(url, timeout=45, allow_redirects=True)
        size = len(response.content)
        alive = response.status_code == 200 and size > 500
        return {
            "event_id": row["event_id"], "attempt_order": order, "source_type": "issuer_or_tdnet_pdf",
            "source_url": url, "attempted_utc": attempted, "http_status": response.status_code,
            "content_bytes": size, "result": "alive" if alive else "dead",
            "evidence_note": f"final_url={response.url}; required status=200 and bytes>500",
        }
    except requests.RequestException as exc:
        return {
            "event_id": row["event_id"], "attempt_order": order, "source_type": "issuer_or_tdnet_pdf",
            "source_url": url, "attempted_utc": attempted, "http_status": "", "content_bytes": 0,
            "result": "request_error", "evidence_note": str(exc)[:200],
        }


def recover():
    rows = read_csv(SAMPLE_OUTPUT)
    if not rows or any(row["sample_locked"] != "True" for row in rows):
        raise RuntimeError("Japan sample is not locked")
    merge_seed_values(rows)
    attempts = []
    for index, row in enumerate(rows):
        if row["seed_fixture"] == "True":
            attempts.append({
                "event_id": row["event_id"], "attempt_order": 1, "source_type": "IRBank",
                "source_url": row["evidence_url"], "attempted_utc": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                "http_status": 403, "content_bytes": 0, "result": "blocked",
                "evidence_note": "Automated source validation denied; no evasion or mass-copy attempted",
            })
            continue
        attempt = attempt_official(row, 1)
        attempts.append(attempt)
        attempts.extend([
            {
                "event_id": row["event_id"], "attempt_order": 2, "source_type": "J-Quants_or_official_statement_data",
                "source_url": "", "attempted_utc": "", "http_status": "", "content_bytes": 0,
                "result": "not_configured", "evidence_note": "No J-Quants entitlement or credential was supplied",
            },
            {
                "event_id": row["event_id"], "attempt_order": 3, "source_type": "IRBank",
                "source_url": f"https://irbank.net/{row['security_code']}/ir", "attempted_utc": "", "http_status": 403,
                "content_bytes": 0, "result": "blocked_after_probe",
                "evidence_note": "Site rejected validation probe; no automated circumvention or bulk copying",
            },
            {
                "event_id": row["event_id"], "attempt_order": 4, "source_type": "Wayback_or_other_archive",
                "source_url": "", "attempted_utc": "", "http_status": "", "content_bytes": 0,
                "result": "not_attempted", "evidence_note": "Deferred after primary/mirror access blockers; failure retained",
            },
        ])
        row["recovery_status"] = "failed"
        row["failure_reason"] = f"official={attempt['result']}; J-Quants unavailable; IRBank 403; archival recovery deferred"
        row["treatment_status"] = "not_attempted_no_clean_numeric_recovery"
        if index + 1 < len(rows):
            time.sleep(2)
    write_csv(SAMPLE_OUTPUT, rows, SAMPLE_FIELDS)
    write_csv(ATTEMPTS_OUTPUT, attempts, ATTEMPT_FIELDS)
    recovered = sum(row["recovery_status"].startswith("recovered") for row in rows)
    meta = json.loads(META_OUTPUT.read_text(encoding="utf-8"))
    meta.update({
        "recovery_attempts_started": True,
        "recovered_provisional": recovered,
        "failed": len(rows) - recovered,
        "recovery_rate_provisional": recovered / len(rows),
        "treatment_complete": sum(row["treatment_status"] == "complete" for row in rows[:10]),
        "note": "Seed values are supplied fixtures; independent IRBank validation was blocked by HTTP 403.",
    })
    write_json(META_OUTPUT, meta)
    print(json.dumps({key: value for key, value in meta.items() if key != "event_ids"}, indent=2, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("freeze", "recover"))
    parser.add_argument("--sample-size", type=int, default=40)
    args = parser.parse_args()
    if args.phase == "freeze":
        freeze_sample(args.sample_size)
    else:
        recover()


if __name__ == "__main__":
    main()

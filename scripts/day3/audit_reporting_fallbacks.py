#!/usr/bin/env python3
"""Audit all periodic reporting fallbacks for earlier results and facility marks."""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DAY2 = Path(__file__).resolve().parents[1] / "day2"
DAY3 = Path(__file__).resolve().parent
sys.path.insert(0, str(DAY2))
sys.path.insert(0, str(DAY3))

from analyze_pre_reveal_power import (  # noqa: E402
    DEVELOPMENT_QUARTER, build_eligible, period_movement_summary,
)
from build_reporting_order_extended import (  # noqa: E402
    accession_base, classify_8k_for_period, filing_rows, parse_timestamp,
)
from common import decimal_or_none, read_csv, sha256_file, write_csv, write_json  # noqa: E402
from reporting_text_utils import normalize_html, parse_submission_documents  # noqa: E402


OUTPUT_FIELDS = [
    "report_period_end", "report_period_label", "ticker", "cik",
    "periodic_fallback_form", "periodic_fallback_accession",
    "periodic_fallback_timestamp_utc", "eight_k_candidates_checked",
    "ex99_exhibits_checked", "soi_present_in_8k", "soi_evidence",
    "exact_facility_mark_present_in_8k", "exact_facility_ids",
    "source_mark_public_timestamp_utc", "source_mark_public_evidence",
    "target_results_public_timestamp_utc", "target_results_public_evidence",
    "target_cutoff_shifted_earlier", "source_mark_timestamp_shifted_earlier",
    "target_and_source_timestamps_differ", "audit_status",
]


def require_user_agent():
    value = os.environ.get("SEC_USER_AGENT", "").strip()
    if "@" not in value:
        raise SystemExit("SEC_USER_AGENT must contain a descriptive name and contact email")
    return value


def fetch_cached(url, cache_path, user_agent):
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    text = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                text = response.read().decode("utf-8", errors="replace")
            break
        except urllib.error.HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == 4:
                raise
            time.sleep(2 ** attempt)
        except (urllib.error.URLError, TimeoutError):
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)
    if text is None:
        raise RuntimeError(f"SEC fetch exhausted retries: {url}")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(text, encoding="utf-8")
    time.sleep(0.25)
    return text


def utc(value):
    return parse_timestamp(value).isoformat().replace("+00:00", "Z")


def compact_text(value):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9.]+", " ", normalize_html(value).lower())).strip()


def number_tokens(value):
    value = decimal_or_none(value)
    if value is None:
        return set()
    values = {value, value / 1000.0, value / 1_000_000.0}
    tokens = set()
    for item in values:
        tokens.add(str(int(round(item))))
        tokens.add(f"{item:.1f}".rstrip("0").rstrip("."))
        tokens.add(f"{item:.2f}".rstrip("0").rstrip("."))
    return {token for token in tokens if len(token) >= 2}


def facility_discriminators(row):
    values = {
        "first_lien": "first lien", "second_lien": "second lien",
        "subordinated": "subordinated", "unsecured": "unsecured",
        "revolver": "revolver", "delayed_draw": "delayed draw",
        "term_loan": "term loan", "note_or_bond": "note",
    }
    return {
        values[value] for value in (row.get("lien"), row.get("facility_type"))
        if value in values
    }


def exact_facility_marks(exhibit_text, facilities):
    plain = compact_text(exhibit_text)
    if "schedule of investments" not in plain:
        return []
    matches = []
    for row in facilities:
        borrower = re.sub(r"[^a-z0-9]+", " ", row.get("borrower_norm", "").lower()).strip()
        if len(borrower) < 5:
            continue
        start = plain.find(borrower)
        if start < 0:
            continue
        window = plain[max(0, start - 250): start + len(borrower) + 900]
        discriminators = facility_discriminators(row)
        if not discriminators or not any(token in window for token in discriminators):
            continue
        values = number_tokens(row.get("fair_value"))
        if not values or not any(re.search(rf"(?<![0-9.]){re.escape(value)}(?![0-9.])", window) for value in values):
            continue
        matches.append(row["economic_facility_id"])
    return sorted(set(matches))


def filing_candidates(submission_rows, period_end, cutoff):
    start = datetime.combine(date.fromisoformat(period_end), datetime.min.time(), tzinfo=timezone.utc)
    end = min(start + timedelta(days=120), parse_timestamp(cutoff))
    return sorted(
        [
            row for row in submission_rows
            if row["form"] == "8-K" and start <= parse_timestamp(row["acceptanceDateTime"]) < end
        ],
        key=lambda row: row["acceptanceDateTime"],
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reporting", type=Path, default=Path("data/day3/reporting_order_extended.csv"))
    parser.add_argument("--facilities", type=Path, default=Path("/private/tmp/finance-day3-sec-cache/bdc_facilities_agg_lineage_v2.csv"))
    parser.add_argument("--cache-dir", type=Path, default=Path("/private/tmp/finance-day3-sec-cache/reporting_order_extended"))
    parser.add_argument("--output", type=Path, default=Path("data/day3/fallback_audit.csv"))
    parser.add_argument("--summary", type=Path, default=Path("data/day3/fallback_audit_summary.json"))
    args = parser.parse_args()

    user_agent = require_user_agent()
    reporting = read_csv(args.reporting)
    facilities = read_csv(args.facilities)
    fallbacks = [row for row in reporting if row["event_type"] in {"10-Q", "10-K"}]
    if len(fallbacks) != 100:
        raise RuntimeError(f"Expected 100 periodic fallbacks, found {len(fallbacks)}")
    current = defaultdict(list)
    by_id = {}
    for row in facilities:
        by_id[row["economic_facility_id"]] = row
        if row["is_current_period"] == "True":
            current[(row["ticker"], row["period_end"])].append(row)

    output = []
    exact_mark_times = {}
    target_overrides = {}
    for index, fallback in enumerate(sorted(fallbacks, key=lambda row: (row["ticker"], row["report_period_end"])), start=1):
        ticker, cik, period_end = fallback["ticker"], fallback["cik"], fallback["report_period_end"]
        payload_path = args.cache_dir / "submissions" / f"CIK{int(cik):010d}.json"
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        candidates = filing_candidates(filing_rows(payload), period_end, fallback["acceptance_timestamp_utc"])
        target_events = []
        source_events = []
        soi_evidence = []
        exhibits_checked = 0
        matched_ids = set()
        for filing in candidates:
            accession = filing["accessionNumber"]
            base = accession_base(cik, accession)
            raw = fetch_cached(
                f"{base}/{accession}.txt",
                args.cache_dir / "filings" / str(int(cik)) / f"{accession}.txt",
                user_agent,
            )
            result, _ = classify_8k_for_period(raw, period_end, "2.02" in (filing.get("items") or ""))
            if result:
                target_events.append((filing["acceptanceDateTime"], accession, result))
            documents = parse_submission_documents(raw)
            for exhibit in (doc for doc in documents if doc["type"].upper().startswith("EX-99")):
                exhibits_checked += 1
                plain = compact_text(exhibit["text"])
                if "schedule of investments" in plain:
                    soi_evidence.append(f"{accession}:{exhibit['filename']}")
                ids = exact_facility_marks(exhibit["text"], current.get((ticker, period_end), []))
                if ids:
                    matched_ids.update(ids)
                    source_events.append((filing["acceptanceDateTime"], accession, exhibit["filename"], ids))

        original = fallback["acceptance_timestamp_utc"]
        if target_events:
            target_time, target_accession, target_result = min(target_events, key=lambda item: item[0])
            target_evidence = f"{target_accession}:{target_result['filename']}; {target_result['evidence']}"
            target_overrides[(ticker, period_end)] = utc(target_time)
        else:
            target_time = original
            target_evidence = f"periodic fallback {fallback['accession']}"
        if source_events:
            source_time, source_accession, source_filename, source_ids = min(source_events, key=lambda item: item[0])
            source_evidence = f"{source_accession}:{source_filename}; exact borrower/facility discriminator and fair-value fact"
            for facility_id in source_ids:
                exact_mark_times[facility_id] = min(
                    utc(source_time), exact_mark_times.get(facility_id, utc(source_time)),
                )
        else:
            source_time = original
            source_evidence = f"SOI/periodic acceptance {fallback['periodic_filing_accession']}"
        target_iso = utc(target_time)
        source_iso = utc(source_time)
        output.append({
            "report_period_end": period_end,
            "report_period_label": fallback["report_period_label"],
            "ticker": ticker,
            "cik": cik,
            "periodic_fallback_form": fallback["form"],
            "periodic_fallback_accession": fallback["accession"],
            "periodic_fallback_timestamp_utc": utc(original),
            "eight_k_candidates_checked": len(candidates),
            "ex99_exhibits_checked": exhibits_checked,
            "soi_present_in_8k": str(bool(soi_evidence)),
            "soi_evidence": "|".join(soi_evidence),
            "exact_facility_mark_present_in_8k": str(bool(source_events)),
            "exact_facility_ids": "|".join(sorted(matched_ids)),
            "source_mark_public_timestamp_utc": source_iso,
            "source_mark_public_evidence": source_evidence,
            "target_results_public_timestamp_utc": target_iso,
            "target_results_public_evidence": target_evidence,
            "target_cutoff_shifted_earlier": str(parse_timestamp(target_iso) < parse_timestamp(original)),
            "source_mark_timestamp_shifted_earlier": str(parse_timestamp(source_iso) < parse_timestamp(original)),
            "target_and_source_timestamps_differ": str(target_iso != source_iso),
            "audit_status": "complete",
        })
        print(f"fallback audit {index}/100: {ticker} {fallback['report_period_label']}", flush=True)

    patched_reporting = [dict(row) for row in reporting]
    for row in patched_reporting:
        override = target_overrides.get((row["ticker"], row["report_period_end"]))
        if override and parse_timestamp(override) < parse_timestamp(row["acceptance_timestamp_utc"]):
            row["acceptance_timestamp_utc"] = override
    patched_facilities = [dict(row) for row in facilities]
    for row in patched_facilities:
        override = exact_mark_times.get(row["economic_facility_id"])
        if override and parse_timestamp(override) < parse_timestamp(row["accepted"]):
            row["accepted"] = override

    before_eligible, _, _ = build_eligible(facilities, reporting)
    after_eligible, _, _ = build_eligible(patched_facilities, patched_reporting)
    before_periods = period_movement_summary(before_eligible, reporting)
    after_periods = period_movement_summary(after_eligible, patched_reporting)
    before_movement = sum(
        value["unique_movement_source_facilities"]
        for key, value in before_periods.items() if key != DEVELOPMENT_QUARTER
    )
    after_movement = sum(
        value["unique_movement_source_facilities"]
        for key, value in after_periods.items() if key != DEVELOPMENT_QUARTER
    )
    write_csv(args.output, sorted(output, key=lambda row: (row["report_period_end"], row["ticker"])), OUTPUT_FIELDS)
    counts = Counter()
    for row in output:
        counts["target_cutoff_shifted"] += row["target_cutoff_shifted_earlier"] == "True"
        counts["source_mark_timestamp_shifted"] += row["source_mark_timestamp_shifted_earlier"] == "True"
        counts["timestamps_differ"] += row["target_and_source_timestamps_differ"] == "True"
        counts["soi_present"] += row["soi_present_in_8k"] == "True"
        counts["exact_facility_mark_present"] += row["exact_facility_mark_present_in_8k"] == "True"
    summary = {
        "fallback_rows_audited": len(output),
        **dict(counts),
        "movement_unique_facilities_before": before_movement,
        "movement_unique_facilities_after": after_movement,
        "movement_guard": 20,
        "movement_guard_remains_met": after_movement >= 20,
        "target_cutoff_rule": "earliest verified results/NAV disclosure",
        "source_facility_timestamp_rule": "earliest exact facility mark; otherwise SOI/10-Q/10-K acceptance",
        "target_current_outcome_used": False,
        "input_hashes": {
            "reporting_order": sha256_file(args.reporting),
            "facilities": sha256_file(args.facilities),
        },
        "output_sha256": sha256_file(args.output),
    }
    write_json(args.summary, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

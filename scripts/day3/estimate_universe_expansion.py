#!/usr/bin/env python3
"""Estimate archive-wide BDC expansion without adding funds to the working sample."""

import argparse
import csv
import io
import json
import os
import sys
import time
import urllib.parse
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import requests

DAY2 = Path(__file__).resolve().parents[1] / "day2"
DAY3 = Path(__file__).resolve().parent
sys.path.insert(0, str(DAY2))
sys.path.insert(0, str(DAY3))

from aggregate_facilities import FIELDS as AGG_FIELDS, aggregate, validate  # noqa: E402
from analyze_pre_reveal_power import mark, seen_aliases  # noqa: E402
from build_eligible_nowcasts import parse_timestamp, strict_same_facility, unique_match  # noqa: E402
from common import (  # noqa: E402
    decimal_or_none, previous_quarter_end, read_csv, sha256_file, write_csv,
    write_json,
)
from parse_bdc_soi import normalize_row, read_submissions  # noqa: E402


DEFAULT_MANIFEST = Path("data/day3/sec_bdc_raw_manifest.csv")
DEFAULT_CACHE = Path("/private/tmp/finance-day3-sec-cache")
DEFAULT_EXISTING_AGG = DEFAULT_CACHE / "bdc_facilities_agg.csv"
DEFAULT_ALL_AGG = DEFAULT_CACHE / "bdc_facilities_all_agg.csv"
DEFAULT_REPORTING = Path("data/day3/reporting_order_extended.csv")
DEFAULT_EXISTING_ELIGIBLE = Path("data/day3/eligible_prefreeze_extended.csv")
DEFAULT_CANDIDATE_META = Path("data/day3/facility_candidates_metadata.json")
DEFAULT_OUTPUT = Path("data/day3/universe_expansion_estimate.csv")
DEFAULT_SUMMARY = Path("data/day3/universe_expansion_summary.json")
DEFAULT_TICKER_CACHE = DEFAULT_CACHE / "company_tickers.json"

NONLISTED_EXISTING = {"BCRED", "HPS", "ASIF", "OCIC"}
MOVEMENT_THRESHOLD = 0.005
MISSING = {"", "unknown", "UNKNOWN"}
WORKING_PERIODS = {
    "2023-12-31", "2024-03-31", "2024-06-30", "2024-09-30",
    "2024-12-31", "2025-03-31", "2025-06-30", "2025-09-30",
}

OUTPUT_FIELDS = [
    "cik", "filer_name", "known_ticker", "listed_status", "manager",
    "acceptance_archives_present", "position_periods_present",
    "aggregated_economic_facilities", "current_period_facilities",
    "key_field_completeness_pct", "spread_completeness_pct", "maturity_completeness_pct",
    "borrower_overlap_with_existing_universe", "candidate_pair_potential",
    "number_of_source_mark_movements", "movements_with_existing_borrower_overlap",
    "exact_timing_feasible_source_movements", "usable_as_listed_target",
    "usable_as_source_only", "reporting_order_reconstruction_appears_feasible",
    "recommended_include_later", "exclusion_reason",
]


def require_user_agent():
    value = os.environ.get("SEC_USER_AGENT", "").strip()
    if "@" not in value:
        raise SystemExit("SEC_USER_AGENT must contain a descriptive name and contact email")
    return value


def archive_path(cache_dir, manifest_row):
    return cache_dir / Path(urllib.parse.urlparse(manifest_row["source_url"]).path).name


def discover_ciks(manifest, cache_dir):
    names = {}
    archives = defaultdict(set)
    for manifest_row in manifest:
        path = archive_path(cache_dir, manifest_row)
        if sha256_file(path) != manifest_row["sha256"]:
            raise RuntimeError(f"Archive checksum mismatch: {path}")
        with zipfile.ZipFile(path) as archive, archive.open(manifest_row["submission_member"]) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""), delimiter="\t")
            for row in reader:
                if row["form"] not in {"10-Q", "10-K"} or not row["cik"]:
                    continue
                cik = str(int(row["cik"]))
                names[cik] = row["name"]
                archives[cik].add(manifest_row["archive_id"])
    return names, archives


def load_company_tickers(cache_path, user_agent):
    if not cache_path.exists():
        response = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers={"User-Agent": user_agent}, timeout=60,
        )
        response.raise_for_status()
        cache_path.write_text(response.text, encoding="utf-8")
        time.sleep(0.16)
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    output = defaultdict(list)
    for item in payload.values():
        output[str(int(item["cik_str"]))].append(item["ticker"])
    return {cik: sorted(set(tickers)) for cik, tickers in output.items()}


def existing_funds(reporting_rows):
    output = {}
    for row in reporting_rows:
        output[str(int(row["cik"]))] = (row["ticker"], row["listed_status"])
    return output


def ticker_universe(names, ticker_map, existing):
    universe = {}
    labels = {}
    for cik in names:
        if cik in existing:
            ticker, status = existing[cik]
        elif ticker_map.get(cik):
            ticker, status = ticker_map[cik][0], "listed"
        else:
            ticker, status = f"CIK{cik}", "unknown"
        universe[cik] = ticker
        labels[cik] = status
    return universe, labels


def parse_archive_rows(manifest_row, cache_dir, universe, seen):
    path = archive_path(cache_dir, manifest_row)
    rows = []
    with zipfile.ZipFile(path) as archive:
        submissions = read_submissions(archive, manifest_row["submission_member"], universe)
        with archive.open(manifest_row["soi_member"]) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""), delimiter="\t")
            required = {"adsh", "cik", "ddate", "period", "Investment, Identifier Axis"}
            if not required <= set(reader.fieldnames or []):
                raise RuntimeError(f"SOI schema missing {sorted(required - set(reader.fieldnames or []))}")
            for line_number, source in enumerate(reader, start=2):
                submission = submissions.get(source["adsh"])
                if not submission:
                    continue
                normalized = normalize_row(
                    source, submission, manifest_row["archive_id"], line_number,
                )
                if not normalized or normalized["facility_row_id"] in seen:
                    continue
                seen.add(normalized["facility_row_id"])
                rows.append(normalized)
    return rows


def build_all_aggregate(manifest, cache_dir, output_path, universe):
    seen = set()
    current = []
    stats = defaultdict(lambda: {
        "aggregated": 0, "current": 0, "periods": set(), "archives": set(),
        "filer_name": "", "field_present": Counter(), "borrowers": set(),
    })
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=AGG_FIELDS, lineterminator="\n")
        writer.writeheader()
        for manifest_row in manifest:
            normalized = parse_archive_rows(manifest_row, cache_dir, universe, seen)
            facilities, _ = aggregate(normalized)
            validate(facilities)
            for row in facilities:
                writer.writerow(row)
                cik = str(int(row["cik"]))
                item = stats[cik]
                item["aggregated"] += 1
                item["archives"].add(row["archive_id"])
                item["filer_name"] = row["filer_name"]
                if row["is_current_period"] == "True":
                    item["current"] += 1
                    item["periods"].add(row["period_end"])
                    item["borrowers"].add(row["borrower_norm"])
                    for field in (
                        "borrower_norm", "debt_equity", "facility_type", "lien", "currency",
                        "reference_rate", "spread", "maturity", "funded_status",
                    ):
                        value = row.get(field, "")
                        present = decimal_or_none(value) is not None if field == "spread" else value not in MISSING
                        item["field_present"][field] += int(present)
                    if row["period_end"] in WORKING_PERIODS:
                        current.append(row)
            print(
                f"{manifest_row['archive_id']}: normalized={len(normalized)} aggregated={len(facilities)}",
                flush=True,
            )
    return current, stats


def load_all_aggregate(output_path):
    """Resume from the outside-Git aggregate after a downstream-only failure."""
    current = []
    stats = defaultdict(lambda: {
        "aggregated": 0, "current": 0, "periods": set(), "archives": set(),
        "filer_name": "", "field_present": Counter(), "borrowers": set(),
    })
    with output_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            cik = str(int(row["cik"]))
            item = stats[cik]
            item["aggregated"] += 1
            item["archives"].add(row["archive_id"])
            item["filer_name"] = row["filer_name"]
            if row["is_current_period"] != "True":
                continue
            item["current"] += 1
            item["periods"].add(row["period_end"])
            item["borrowers"].add(row["borrower_norm"])
            for field in (
                "borrower_norm", "debt_equity", "facility_type", "lien", "currency",
                "reference_rate", "spread", "maturity", "funded_status",
            ):
                value = row.get(field, "")
                present = decimal_or_none(value) is not None if field == "spread" else value not in MISSING
                item["field_present"][field] += int(present)
            if row["period_end"] in WORKING_PERIODS:
                current.append(row)
    return current, stats


def pct(count, denominator):
    return round(count / denominator * 100, 3) if denominator else 0.0


def current_index(rows):
    output = defaultdict(list)
    for row in rows:
        output[(row["period_end"], str(int(row["cik"])), row["borrower_norm"])].append(row)
    return output


def movement_events(rows):
    index = current_index(rows)
    events = []
    excluded = seen_aliases()
    for row in rows:
        if row["borrower_norm"] in excluded:
            continue
        prior_period = previous_quarter_end(row["period_end"])
        prior = unique_match(
            row, index.get((prior_period, str(int(row["cik"])), row["borrower_norm"]), [])
        )
        current_mark, prior_mark = mark(row), mark(prior) if prior else None
        if current_mark is None or prior_mark is None or abs(current_mark - prior_mark) < MOVEMENT_THRESHOLD:
            continue
        events.append({"current": row, "prior": prior, "delta": current_mark - prior_mark})
    return events, index


def reporting_cutoffs(reporting_rows, all_current):
    output = {}
    existing_ciks = set()
    for row in reporting_rows:
        cik = str(int(row["cik"]))
        existing_ciks.add(cik)
        if row["verification_status"] != "explicit_missing" and row["acceptance_timestamp_utc"]:
            output[(cik, row["report_period_end"])] = row["acceptance_timestamp_utc"]
    periodic = defaultdict(list)
    for row in all_current:
        periodic[(str(int(row["cik"])), row["period_end"])].append(row["accepted"])
    for key, values in periodic.items():
        output.setdefault(key, min(values))
    return output, existing_ciks


def feasible_event(event, target_cik, index, cutoffs):
    source = event["current"]
    source_cik = str(int(source["cik"]))
    if source_cik == target_cik:
        return False
    prior_period = previous_quarter_end(source["period_end"])
    target_prior = unique_match(
        source, index.get((prior_period, target_cik, source["borrower_norm"]), [])
    )
    target_cutoff = cutoffs.get((target_cik, source["period_end"]))
    if not target_prior or not target_cutoff:
        return False
    source_info = source["accepted"]
    return (
        parse_timestamp(target_prior["accepted"]) < parse_timestamp(source_info)
        < parse_timestamp(target_cutoff)
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--existing-aggregate", type=Path, default=DEFAULT_EXISTING_AGG)
    parser.add_argument("--all-aggregate-cache", type=Path, default=DEFAULT_ALL_AGG)
    parser.add_argument("--reporting", type=Path, default=DEFAULT_REPORTING)
    parser.add_argument("--existing-eligible", type=Path, default=DEFAULT_EXISTING_ELIGIBLE)
    parser.add_argument("--candidate-meta", type=Path, default=DEFAULT_CANDIDATE_META)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--ticker-cache", type=Path, default=DEFAULT_TICKER_CACHE)
    args = parser.parse_args()
    manifest = read_csv(args.manifest)
    reporting = read_csv(args.reporting)
    names, archive_sets = discover_ciks(manifest, args.cache_dir)
    ticker_map = load_company_tickers(args.ticker_cache, require_user_agent())
    existing = existing_funds(reporting)
    universe, listed_labels = ticker_universe(names, ticker_map, existing)
    if args.all_aggregate_cache.exists():
        print(f"Reusing outside-Git aggregate cache: {args.all_aggregate_cache}", flush=True)
        all_current, stats = load_all_aggregate(args.all_aggregate_cache)
    else:
        all_current, stats = build_all_aggregate(
            manifest, args.cache_dir, args.all_aggregate_cache, universe,
        )

    existing_rows = read_csv(args.existing_aggregate)
    existing_borrowers = defaultdict(list)
    for row in existing_rows:
        if row["is_current_period"] == "True":
            existing_borrowers[(row["period_end"], row["borrower_norm"])].append(row)
    events, all_index = movement_events(all_current)
    events_by_cik = defaultdict(list)
    for event in events:
        events_by_cik[str(int(event["current"]["cik"]))].append(event)
    cutoffs, existing_ciks = reporting_cutoffs(reporting, all_current)
    existing_listed_ciks = {
        cik for cik, (_, status) in existing.items() if status == "listed"
    }

    rows = []
    recommendations = set()
    for cik in sorted(names, key=int):
        item = stats[cik]
        current_count = item["current"]
        completeness_fields = (
            "borrower_norm", "debt_equity", "facility_type", "lien", "currency",
            "reference_rate", "spread", "maturity", "funded_status",
        )
        completeness = sum(
            pct(item["field_present"][field], current_count) for field in completeness_fields
        ) / len(completeness_fields) if current_count else 0.0
        spread_pct = pct(item["field_present"]["spread"], current_count)
        maturity_pct = pct(item["field_present"]["maturity"], current_count)
        overlap_borrowers = {
            borrower for borrower in item["borrowers"]
            if any(key[1] == borrower for key in existing_borrowers)
        }
        candidate_potential = 0
        for row in all_current:
            if str(int(row["cik"])) != cik:
                continue
            candidate_potential += sum(
                other["cik"] != row["cik"]
                for other in existing_borrowers.get((row["period_end"], row["borrower_norm"]), [])
            )
        fund_events = events_by_cik.get(cik, [])
        overlap_movements = sum(
            bool(existing_borrowers.get((event["current"]["period_end"], event["current"]["borrower_norm"])))
            for event in fund_events
        )
        feasible_source = sum(
            any(feasible_event(event, target, all_index, cutoffs) for target in existing_listed_ciks)
            for event in fund_events
        )
        reporting_feasible = len(item["periods"]) >= 4
        listed = listed_labels[cik]
        recommended = (
            cik not in existing_ciks and current_count >= 100 and reporting_feasible
            and candidate_potential > 0 and len(fund_events) > 0 and completeness >= 40
        )
        if recommended:
            recommendations.add(cik)
        reasons = []
        if cik in existing_ciks:
            reasons.append("already in 19-fund universe")
        if current_count < 100:
            reasons.append("fewer than 100 current-period facilities")
        if not reporting_feasible:
            reasons.append("fewer than four position periods")
        if not candidate_potential:
            reasons.append("no borrower-overlap candidate potential with existing universe")
        if not fund_events:
            reasons.append("no computable >=0.5pp source movements")
        rows.append({
            "cik": cik,
            "filer_name": item["filer_name"] or names[cik],
            "known_ticker": universe[cik] if not universe[cik].startswith("CIK") else "",
            "listed_status": listed,
            "manager": "",
            "acceptance_archives_present": "|".join(sorted(archive_sets[cik])),
            "position_periods_present": "|".join(sorted(item["periods"])),
            "aggregated_economic_facilities": item["aggregated"],
            "current_period_facilities": current_count,
            "key_field_completeness_pct": round(completeness, 3),
            "spread_completeness_pct": spread_pct,
            "maturity_completeness_pct": maturity_pct,
            "borrower_overlap_with_existing_universe": len(overlap_borrowers),
            "candidate_pair_potential": candidate_potential,
            "number_of_source_mark_movements": len(fund_events),
            "movements_with_existing_borrower_overlap": overlap_movements,
            "exact_timing_feasible_source_movements": feasible_source,
            "usable_as_listed_target": str(listed == "listed" and reporting_feasible and current_count >= 100),
            "usable_as_source_only": str(listed != "listed" and reporting_feasible and current_count >= 100),
            "reporting_order_reconstruction_appears_feasible": str(reporting_feasible),
            "recommended_include_later": str(recommended),
            "exclusion_reason": " | ".join(reasons),
        })
    write_csv(args.output, rows, OUTPUT_FIELDS)

    recommended_listed = {cik for cik in recommendations if listed_labels[cik] == "listed"}
    all_additional_listed = {
        cik for cik in names if cik not in existing_ciks and listed_labels[cik] == "listed"
        and stats[cik]["current"] >= 100 and len(stats[cik]["periods"]) >= 4
    }
    all_feasible_sources = {
        cik for cik in names if cik not in existing_ciks and stats[cik]["current"] >= 100
        and len(stats[cik]["periods"]) >= 4
    }
    existing_eligible = read_csv(args.existing_eligible)
    existing_event_ids = {
        (row["report_period_end"], row["source_cik"], row["source_facility_id"])
        for row in existing_eligible if row["movement_eligible"] == "True"
        and row["report_period_label"] != "2025Q3"
    }

    def expanded_event_ids(source_ciks, target_ciks):
        output = set(existing_event_ids)
        for event in events:
            source = event["current"]
            source_cik = str(int(source["cik"]))
            if source["period_end"] == "2025-09-30" or source_cik not in source_ciks:
                continue
            if any(feasible_event(event, target, all_index, cutoffs) for target in target_ciks):
                output.add((source["period_end"], source_cik, source["economic_facility_id"]))
        return output

    conservative_ids = expanded_event_ids(recommendations, existing_listed_ciks)
    base_sources = existing_ciks | recommendations
    base_targets = existing_listed_ciks | recommended_listed
    base_ids = expanded_event_ids(base_sources, base_targets)
    optimistic_sources = existing_ciks | all_feasible_sources
    optimistic_targets = existing_listed_ciks | all_additional_listed
    optimistic_ids = expanded_event_ids(optimistic_sources, optimistic_targets)
    current_candidate_count = json.loads(args.candidate_meta.read_text(encoding="utf-8"))["candidate_pair_count"]
    additional_candidate_potential = sum(
        int(row["candidate_pair_potential"]) for row in rows if row["cik"] in recommendations
    )
    summary = {
        "archive_manifest_sha256": sha256_file(args.manifest),
        "all_aggregate_cache_sha256": sha256_file(args.all_aggregate_cache),
        "output_sha256": sha256_file(args.output),
        "total_unique_bdc_cik_in_archives": len(names),
        "funds_with_at_least_100_aggregated_facilities": sum(int(row["aggregated_economic_facilities"]) >= 100 for row in rows),
        "funds_with_spread_completeness_at_least_50pct": sum(float(row["spread_completeness_pct"]) >= 50 for row in rows),
        "funds_with_maturity_completeness_at_least_50pct": sum(float(row["maturity_completeness_pct"]) >= 50 for row in rows),
        "funds_with_both_spread_and_maturity_at_least_50pct": sum(
            float(row["spread_completeness_pct"]) >= 50 and float(row["maturity_completeness_pct"]) >= 50
            for row in rows
        ),
        "recommended_additional_funds": len(recommendations),
        "manager_field_status": "left blank because manager is not a deterministic field in the SEC BDC flat-file/submission metadata used for this screen",
        "additional_listed_targets": len(recommended_listed),
        "additional_nonlisted_or_unknown_sources": len(recommendations - recommended_listed),
        "estimated_candidate_pair_multiplier": round((current_candidate_count + additional_candidate_potential) / current_candidate_count, 3),
        "estimated_movement_event_multiplier_base": round(len(base_ids) / len(existing_event_ids), 3) if existing_event_ids else None,
        "current_untouched_movement_count": len(existing_event_ids),
        "conservative_estimated_movement_count": len(conservative_ids),
        "base_estimated_movement_count": len(base_ids),
        "optimistic_estimated_movement_count": len(optimistic_ids),
        "estimate_definitions": {
            "conservative": "current events plus recommended additional sources that have exact prior-facility and timing opportunities versus existing listed targets",
            "base": "conservative universe plus recommended additional listed targets; periodic acceptance is the added-fund results cutoff",
            "optimistic": "all additional funds with >=100 current facilities and >=4 periods; all exchange-ticker funds may be targets",
        },
        "working_sample_expanded": False,
        "freeze_or_reveal_authorized": False,
        "raw_normalized_or_aggregate_data_committed": False,
    }
    write_json(args.summary, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

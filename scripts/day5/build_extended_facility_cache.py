#!/usr/bin/env python3
"""Parse new official monthly archives with the locked Day 3 facility pipeline."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import urllib.parse
import zipfile
from collections import Counter
from pathlib import Path


DAY2 = Path(__file__).resolve().parents[1] / "day2"
DAY3 = Path(__file__).resolve().parents[1] / "day3"
sys.path.insert(0, str(DAY2))
sys.path.insert(0, str(DAY3))

from aggregate_facilities import FIELDS as AGG_FIELDS, aggregate, validate  # noqa: E402
from common import read_csv, sha256_file, write_json  # noqa: E402
from parse_bdc_soi import normalize_row, read_submissions  # noqa: E402


csv.field_size_limit(sys.maxsize)

DEFAULT_MANIFEST = Path("data/day5/sec_bdc_archive_manifest.csv")
DEFAULT_CACHE = Path("/private/tmp/finance-day5-sec-cache/raw")
DEFAULT_UNIVERSE = Path("data/day3/universe_expansion_estimate.csv")
DEFAULT_TICKERS = Path("/private/tmp/finance-day3-sec-cache/company_tickers.json")
DEFAULT_OUTPUT = Path("/private/tmp/finance-day5-sec-cache/bdc_facilities_2026_new_agg.csv")
DEFAULT_METADATA = Path("data/day5/new_quarter_facility_metadata.json")


def archive_path(cache: Path, row: dict[str, str]) -> Path:
    path = cache / row["sec_filename"]
    if not path.exists():
        raise FileNotFoundError(path)
    if sha256_file(path) != row["sha256"]:
        raise RuntimeError(f"Raw archive checksum mismatch: {path}")
    return path


def known_tickers(universe_path: Path, ticker_path: Path) -> dict[str, str]:
    output = {}
    for row in read_csv(universe_path):
        ticker = row["known_ticker"].strip()
        if ticker:
            output[str(int(row["cik"]))] = ticker
    payload = json.loads(ticker_path.read_text(encoding="utf-8"))
    by_cik = {}
    for item in payload.values():
        by_cik.setdefault(str(int(item["cik_str"])), []).append(item["ticker"])
    for cik, tickers in by_cik.items():
        output.setdefault(cik, sorted(set(tickers))[0])
    return output


def discover_universe(
    manifest: list[dict[str, str]], cache: Path, known: dict[str, str],
) -> dict[str, str]:
    ciks = set()
    for row in manifest:
        if not row["soi_member"]:
            continue
        with zipfile.ZipFile(archive_path(cache, row)) as archive:
            with archive.open(row["submission_member"]) as raw:
                reader = csv.DictReader(
                    io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""), delimiter="\t"
                )
                for item in reader:
                    if item.get("cik") and item.get("form") in {"10-Q", "10-K"}:
                        ciks.add(str(int(item["cik"])))
    return {cik: known.get(cik, f"CIK{cik}") for cik in sorted(ciks, key=int)}


def parse_month(
    row: dict[str, str], cache: Path, universe: dict[str, str], seen: set[str],
) -> tuple[list[dict[str, str]], dict]:
    if not row["soi_member"]:
        return [], {
            "archive_id": row["archive_id"],
            "raw_soi_rows": 0,
            "normalized_rows": 0,
            "duplicate_rows_removed": 0,
            "status": "no_financial_soi_table",
        }
    normalized = []
    raw_count = 0
    duplicate_count = 0
    with zipfile.ZipFile(archive_path(cache, row)) as archive:
        submissions = read_submissions(archive, row["submission_member"], universe)
        with archive.open(row["soi_member"]) as raw:
            reader = csv.DictReader(
                io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""), delimiter="\t"
            )
            required = {"adsh", "cik", "ddate", "period", "Investment, Identifier Axis"}
            if not required <= set(reader.fieldnames or []):
                raise RuntimeError(
                    f"SOI schema missing {sorted(required - set(reader.fieldnames or []))} "
                    f"for {row['archive_id']}"
                )
            for line_number, source in enumerate(reader, start=2):
                submission = submissions.get(source["adsh"])
                if not submission:
                    continue
                raw_count += 1
                item = normalize_row(source, submission, row["archive_id"], line_number)
                if not item:
                    continue
                if item["facility_row_id"] in seen:
                    duplicate_count += 1
                    continue
                seen.add(item["facility_row_id"])
                normalized.append(item)
    return normalized, {
        "archive_id": row["archive_id"],
        "raw_soi_rows": raw_count,
        "normalized_rows": len(normalized),
        "duplicate_rows_removed": duplicate_count,
        "status": "parsed_with_locked_normalization",
    }


def write_aggregate(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=AGG_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--universe-estimate", type=Path, default=DEFAULT_UNIVERSE)
    parser.add_argument("--ticker-cache", type=Path, default=DEFAULT_TICKERS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    args = parser.parse_args()

    manifest = read_csv(args.manifest)
    known = known_tickers(args.universe_estimate, args.ticker_cache)
    universe = discover_universe(manifest, args.cache_dir, known)
    normalized = []
    seen = set()
    by_archive = []
    for row in manifest:
        values, stats = parse_month(row, args.cache_dir, universe, seen)
        normalized.extend(values)
        by_archive.append(stats)
        print(
            f"{row['archive_id']}: raw={stats['raw_soi_rows']} "
            f"normalized={stats['normalized_rows']} duplicates={stats['duplicate_rows_removed']}"
        )
    facilities, dropped = aggregate(normalized)
    validate(facilities)
    write_aggregate(args.output, facilities)
    periods = Counter(
        row["period_end"] for row in facilities if row["is_current_period"] == "True"
    )
    metadata = {
        "status": "new_months_parsed_with_locked_pipeline",
        "normalization_implementation": "scripts/day2/parse_bdc_soi.py::normalize_row",
        "aggregation_implementation": "scripts/day3/aggregate_facilities.py::economic_facility_v2",
        "normalization_rules_changed": False,
        "aggregation_rules_changed": False,
        "matcher_rules_changed": False,
        "manifest_sha256": sha256_file(args.manifest),
        "raw_archives": len(manifest),
        "universe_ciks_in_new_months": len(universe),
        "normalized_rows": len(normalized),
        "issuer_total_rows_dropped": len(dropped),
        "economic_facility_rows": len(facilities),
        "current_period_facility_rows": sum(
            row["is_current_period"] == "True" for row in facilities
        ),
        "current_period_ends": dict(sorted(periods.items())),
        "required_periods_recovered": {
            "2025-12-31": periods["2025-12-31"],
            "2026-03-31": periods["2026-03-31"],
        },
        "by_archive": by_archive,
        "output_cache": str(args.output),
        "output_sha256": sha256_file(args.output),
        "raw_and_aggregate_storage": "outside Git",
        "target_current_numeric_outcomes_materialized_to_git": False,
    }
    write_json(args.metadata, metadata)
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

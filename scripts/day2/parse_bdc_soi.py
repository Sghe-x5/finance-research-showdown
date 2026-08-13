#!/usr/bin/env python3
"""Parse SEC BDC SOI tables into a normalized, cache-only facility file."""

import argparse
import csv
import io
import json
import urllib.parse
import zipfile
from pathlib import Path

from common import (
    canonical_json, clean_member, debt_equity, decimal_or_none, facility_type,
    funded_status, iso_date_or_blank, lien_category, normalize_borrower,
    read_csv, reference_rate, sha256_bytes, sha256_file, stable_id, write_json,
)


DEFAULT_CACHE = Path("/private/tmp/finance-day2-sec-cache")
DEFAULT_MANIFEST = Path("data/day2/raw_manifest.csv")
DEFAULT_OUTPUT = DEFAULT_CACHE / "bdc_soi_normalized.csv"
DEFAULT_METADATA = Path("data/day2/bdc_normalized_metadata.json")

OUTPUT_FIELDS = [
    "facility_row_id", "archive_id", "adsh", "accepted", "cik", "ticker",
    "filer_name", "form", "filed", "period_end", "observation_date",
    "is_current_period", "investment_identifier", "borrower_raw", "borrower_norm",
    "debt_equity", "facility_type", "lien", "currency", "reference_rate",
    "spread", "total_interest_rate", "pik_rate", "maturity", "funded_status",
    "acquisition_date", "principal", "cost", "fair_value", "non_accrual",
    "restructuring_flag", "issuer_affiliation", "source_concepts_json",
    "raw_provenance", "raw_row_sha256",
]

CONCEPTS = {
    "investment_identifier": [
        "Investment, Identifier Axis", "Investment, Name Axis",
        "Investment, Issuer Name Axis", "PortfolioCompanies", "Investment Axis",
    ],
    "facility_type": [
        "Investment Type Axis", "InvestmentSubType", "Debt Instrument Axis",
        "Long-term Debt, Type Axis", "Financial Instrument Axis",
    ],
    "lien": ["Lien Category Axis", "Investment Type Axis"],
    "currency": ["Currency Axis", "Derivative, Currency Bought"],
    "reference_rate": [
        "RateType", "Variable Rate Axis", "VariableRateComponent",
        "Investment, Variable Interest Rate, Type [Extensible Enumeration]",
        "Debt Instrument, Interest Rate Terms",
    ],
    "spread": [
        "Investment, Basis Spread, Variable Rate",
        "Debt Instrument, Basis Spread on Variable Rate",
        "Loans Receivable, Basis Spread on Variable Rate",
    ],
    "total_interest_rate": [
        "Investment Interest Rate", "Debt Instrument, Interest Rate During Period",
        "Investment, Interest Rate, Paid in Cash",
    ],
    "pik_rate": ["Investment, Interest Rate, Paid in Kind", "Paid-in-Kind Interest"],
    "maturity": ["Investment Maturity Date", "Derivative, Contract End Date"],
    "acquisition_date": ["Investment, Acquisition Date", "Award Date Axis"],
    "principal": [
        "Investment Owned, Balance, Principal Amount", "Investment Owned, Face Amount",
        "Debt Securities, Available-for-Sale, Amortized Cost",
    ],
    "cost": [
        "Adjusted cost basis", "Investment Owned, Cost",
        "Debt Securities, Trading, and Equity Securities, FV-NI, Cost",
        "Debt Securities, Available-for-Sale, Amortized Cost",
    ],
    "fair_value": [
        "Initial fair value of Investment", "Investment Owned, Fair Value",
        "Investments, Fair Value Disclosure", "Debt Securities, Held-to-Maturity, Fair Value",
    ],
    "non_accrual": [
        "Investment, Non-income Producing [true false]",
        "Financial Instrument Performance Status Axis",
    ],
    "issuer_affiliation": ["Investment, Issuer Affiliation Axis"],
}


def pick(row, names):
    for name in names:
        value = (row.get(name) or "").strip()
        if value:
            return value, name
    return "", ""


def load_universe(reporting_order_path):
    rows = read_csv(reporting_order_path)
    universe = {}
    for row in rows:
        universe[str(int(row["cik"]))] = row["ticker"]
    if not universe:
        raise RuntimeError("BDC universe is empty")
    return universe


def read_submissions(archive, member, universe):
    submissions = {}
    with archive.open(member) as raw:
        reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""), delimiter="\t")
        required = {"adsh", "cik", "name", "form", "period", "accepted", "filed"}
        if not required <= set(reader.fieldnames or []):
            raise RuntimeError(f"Submission schema missing {sorted(required - set(reader.fieldnames or []))}")
        for row in reader:
            cik = str(int(row["cik"])) if row["cik"] else ""
            if cik not in universe or row["form"] not in {"10-Q", "10-K"}:
                continue
            submissions[row["adsh"]] = {
                "adsh": row["adsh"],
                "cik": cik,
                "ticker": universe[cik],
                "filer_name": row["name"],
                "form": row["form"],
                "period_end": iso_date_or_blank(row["period"]),
                "accepted": row["accepted"],
                "filed": row["filed"],
            }
    return submissions


def normalize_row(row, submission, archive_id, line_number):
    values = {}
    source_concepts = {}
    for canonical, names in CONCEPTS.items():
        value, concept = pick(row, names)
        values[canonical] = clean_member(value)
        if concept:
            source_concepts[canonical] = concept

    identifier = values["investment_identifier"]
    if not identifier:
        return None
    numeric = [decimal_or_none(values[name]) for name in ("principal", "cost", "fair_value")]
    if sum(value is not None for value in numeric) < 2:
        return None

    type_raw = values["facility_type"]
    lien_raw = values["lien"]
    rate_raw = values["reference_rate"]
    observation_date = iso_date_or_blank(row.get("ddate"))
    period_end = submission["period_end"]
    raw_nonempty = {key: value for key, value in row.items() if value}
    raw_sha = sha256_bytes(canonical_json(raw_nonempty).encode("utf-8"))
    provenance = f"{archive_id}:{line_number}"
    row_id = stable_id(submission["adsh"], observation_date, identifier, raw_sha)
    combined = " ".join((identifier, type_raw, lien_raw, rate_raw)).lower()
    non_accrual = values["non_accrual"].lower()
    return {
        "facility_row_id": row_id,
        "archive_id": archive_id,
        "adsh": submission["adsh"],
        "accepted": submission["accepted"],
        "cik": submission["cik"],
        "ticker": submission["ticker"],
        "filer_name": submission["filer_name"],
        "form": submission["form"],
        "filed": submission["filed"],
        "period_end": period_end,
        "observation_date": observation_date,
        "is_current_period": str(observation_date == period_end),
        "investment_identifier": identifier,
        "borrower_raw": identifier,
        "borrower_norm": normalize_borrower(identifier),
        "debt_equity": debt_equity(identifier, type_raw, lien_raw),
        "facility_type": facility_type(identifier, type_raw),
        "lien": lien_category(identifier, lien_raw, type_raw),
        "currency": values["currency"].upper() or "UNKNOWN",
        "reference_rate": reference_rate(identifier, rate_raw),
        "spread": values["spread"],
        "total_interest_rate": values["total_interest_rate"],
        "pik_rate": values["pik_rate"],
        "maturity": iso_date_or_blank(values["maturity"]),
        "funded_status": funded_status(identifier, type_raw),
        "acquisition_date": iso_date_or_blank(values["acquisition_date"]),
        "principal": values["principal"],
        "cost": values["cost"],
        "fair_value": values["fair_value"],
        "non_accrual": str(non_accrual in {"1", "true", "yes"} or "nonaccrual" in combined),
        "restructuring_flag": str(any(token in combined for token in ("restructur", "amend", "default"))),
        "issuer_affiliation": values["issuer_affiliation"],
        "source_concepts_json": canonical_json(source_concepts),
        "raw_provenance": provenance,
        "raw_row_sha256": raw_sha,
    }


def parse_archive(cache_dir, manifest_row, universe, writer, seen):
    filename = Path(urllib.parse.urlparse(manifest_row["source_url"]).path).name
    archive_path = cache_dir / filename
    if not archive_path.exists():
        raise FileNotFoundError(f"Raw ZIP missing from external cache: {archive_path}")
    if sha256_file(archive_path) != manifest_row["sha256"]:
        raise RuntimeError(f"Raw ZIP checksum mismatch: {archive_path}")

    raw_rows = 0
    normalized_rows = 0
    duplicate_rows = 0
    with zipfile.ZipFile(archive_path) as archive:
        submissions = read_submissions(archive, manifest_row["submission_member"], universe)
        with archive.open(manifest_row["soi_member"]) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""), delimiter="\t")
            required = {"adsh", "cik", "ddate", "period", "Investment, Identifier Axis"}
            if not required <= set(reader.fieldnames or []):
                raise RuntimeError(f"SOI schema missing {sorted(required - set(reader.fieldnames or []))}")
            for line_number, row in enumerate(reader, start=2):
                if row["adsh"] not in submissions:
                    continue
                raw_rows += 1
                normalized = normalize_row(row, submissions[row["adsh"]], manifest_row["archive_id"], line_number)
                if not normalized:
                    continue
                if normalized["facility_row_id"] in seen:
                    duplicate_rows += 1
                    continue
                seen.add(normalized["facility_row_id"])
                writer.writerow(normalized)
                normalized_rows += 1
    return raw_rows, normalized_rows, duplicate_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--reporting-order", type=Path, default=Path("02_showdown/reporting_order.csv"))
    args = parser.parse_args()

    manifest = read_csv(args.manifest)
    universe = load_universe(args.reporting_order)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    totals = {"raw_soi_rows_for_universe": 0, "normalized_facility_rows": 0, "duplicates_removed": 0}
    by_archive = []
    seen = set()
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in manifest:
            raw_count, normalized_count, duplicate_count = parse_archive(args.cache_dir, row, universe, writer, seen)
            by_archive.append({
                "archive_id": row["archive_id"], "raw_soi_rows_for_universe": raw_count,
                "normalized_facility_rows": normalized_count, "duplicates_removed": duplicate_count,
            })
            totals["raw_soi_rows_for_universe"] += raw_count
            totals["normalized_facility_rows"] += normalized_count
            totals["duplicates_removed"] += duplicate_count
            print(f"{row['archive_id']}: raw={raw_count} normalized={normalized_count} duplicates={duplicate_count}")

    metadata = {
        "schema_version": 1,
        "manifest_sha256": sha256_file(args.manifest),
        "normalized_sha256": sha256_file(args.output),
        "universe_cik_count": len(universe),
        "by_archive": by_archive,
        **totals,
        "storage": "normalized rows cached outside Git; only this metadata is committed",
    }
    write_json(args.metadata, metadata)
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

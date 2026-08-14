#!/usr/bin/env python3
"""Repair exact SEC-tagged facility fields omitted by the Day 2 parser.

Only official wide-SOI columns and explicitly tagged supporting XBRL facts are
used.  Identifier prose is never parsed for these four fields.
"""

import argparse
import csv
import io
import json
import re
import sys
import urllib.parse
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

DAY2 = Path(__file__).resolve().parents[1] / "day2"
DAY3 = Path(__file__).resolve().parent
sys.path.insert(0, str(DAY2))
sys.path.insert(0, str(DAY3))

from common import (  # noqa: E402
    canonical_json, clean_member, read_csv, sha256_file, write_json,
)
from parse_bdc_soi import OUTPUT_FIELDS  # noqa: E402
from audit_field_lineage import (  # noqa: E402
    DIRECT_COLUMNS, archive_path, currency_members, extract_investment_member,
    load_manifest, load_universe, read_archive_submissions, sec_date, semantic_field,
)

csv.field_size_limit(sys.maxsize)

FIELDS = ("maturity", "currency", "reference_rate", "acquisition_date")


def normalized_date(value):
    value = str(value or "").strip()
    if re.fullmatch(r"\d{8}", value):
        value = f"{value[:4]}-{value[4:6]}-{value[6:]}"
    if re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", value):
        return value
    return ""


def canonical_currency(value):
    value = clean_member(value)
    if not value:
        return ""
    if "#" in value:
        value = value.rsplit("#", 1)[-1]
    aliases = {
        "US Dollar": "USD", "United States Dollar": "USD", "Euro": "EUR",
        "British Pound": "GBP", "Canadian Dollar": "CAD", "Australian Dollar": "AUD",
    }
    return aliases.get(value, value.upper())


def canonical_reference_rate(value):
    """Canonicalize an official tag/member value, not identifier prose."""
    value = clean_member(value)
    if not value:
        return ""
    if "#" in value:
        value = value.rsplit("#", 1)[-1]
    text = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    mappings = (
        (("secured overnight financing rate", "sofr"), "SOFR"),
        (("london interbank offered rate", "libor"), "LIBOR"),
        (("euro interbank offered rate", "euribor"), "EURIBOR"),
        (("sterling overnight index average", "sonia"), "SONIA"),
        (("euro short term rate", "ester", "estr"), "ESTR"),
        (("canadian overnight repo rate average", "corra"), "CORRA"),
        (("canadian dollar offered rate", "cdor"), "CDOR"),
        (("bloomberg short term bank yield", "bsby"), "BSBY"),
        (("prime rate", "prime"), "PRIME"),
        (("base rate", "alternate base rate", "abr"), "BASE_RATE"),
        (("fixed rate", "fixed"), "FIXED"),
    )
    for aliases, canonical in mappings:
        if any(alias in text for alias in aliases):
            return canonical
    return ""


def normalize_field(field, value):
    if field in {"maturity", "acquisition_date"}:
        return normalized_date(value)
    if field == "currency":
        return canonical_currency(value)
    if field == "reference_rate":
        return canonical_reference_rate(value)
    raise KeyError(field)


def add_candidate(store, key, field, value, source):
    value = normalize_field(field, value)
    if value:
        store[(key, field)][value].add(source)


def collect_archive_corrections(path, manifest_row, universe):
    candidates = defaultdict(lambda: defaultdict(set))
    with zipfile.ZipFile(path) as archive:
        submissions = read_archive_submissions(archive, manifest_row["submission_member"], universe)
        with archive.open(manifest_row["soi_member"]) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""), delimiter="\t")
            for line_number, row in enumerate(reader, start=2):
                if row.get("adsh") not in submissions:
                    continue
                identifier = clean_member(row.get("Investment, Identifier Axis", ""))
                if not identifier:
                    continue
                key = (manifest_row["archive_id"], row["adsh"], sec_date(row.get("ddate")), identifier)
                for field, columns in DIRECT_COLUMNS.items():
                    for column in columns:
                        if row.get(column):
                            add_candidate(candidates, key, field, row[column], f"soi.tsv:{line_number}:{column}")

        tag_fields = {}
        with archive.open("datasets/tag.tsv") as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""), delimiter="\t")
            for row in reader:
                field = semantic_field(row.get("tag"), row.get("tlabel"), row.get("doc"))
                if field:
                    tag_fields[(row["tag"], row["version"])] = field

        for table in ("datasets/num.tsv", "datasets/txt.tsv", "datasets/non.tsv"):
            with archive.open(table) as raw:
                reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""), delimiter="\t")
                for line_number, row in enumerate(reader, start=2):
                    if row.get("adsh") not in submissions:
                        continue
                    member = extract_investment_member(row.get("segments"))
                    if not member:
                        continue
                    key = (
                        manifest_row["archive_id"], row["adsh"], sec_date(row.get("ddate")),
                        clean_member(member),
                    )
                    field = tag_fields.get((row.get("tag", ""), row.get("version", "")), "")
                    if field:
                        add_candidate(
                            candidates, key, field, row.get("value"),
                            f"{table}:{line_number}:{row['tag']}@{row['version']}",
                        )
                    for currency in currency_members(row.get("segments")):
                        add_candidate(candidates, key, "currency", currency, f"{table}:{line_number}:CurrencyAxis")
    return candidates


def merge_candidates(all_candidates, additions):
    for key, values in additions.items():
        for value, sources in values.items():
            all_candidates[key][value].update(sources)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("data/day3/sec_bdc_raw_manifest.csv"))
    parser.add_argument("--cache-dir", type=Path, default=Path("/private/tmp/finance-day3-sec-cache"))
    parser.add_argument("--reporting-order", type=Path, default=Path("data/day3/reporting_order_extended.csv"))
    parser.add_argument("--input", type=Path, default=Path("/private/tmp/finance-day3-sec-cache/bdc_soi_normalized.csv"))
    parser.add_argument("--output", type=Path, default=Path("/private/tmp/finance-day3-sec-cache/bdc_soi_normalized_lineage_v2.csv"))
    parser.add_argument("--metadata", type=Path, default=Path("data/day3/bdc_normalized_lineage_v2_metadata.json"))
    args = parser.parse_args()

    universe = load_universe(args.reporting_order)
    manifest = load_manifest(args.manifest)
    candidates = defaultdict(lambda: defaultdict(set))
    for manifest_row in manifest:
        path = archive_path(args.cache_dir, manifest_row)
        merge_candidates(candidates, collect_archive_corrections(path, manifest_row, universe))
        print(f"lineage repair scan: {manifest_row['archive_id']}", flush=True)

    unique = {}
    conflicts = {}
    for key, values in candidates.items():
        if len(values) == 1:
            value, sources = next(iter(values.items()))
            unique[key] = (value, sorted(sources))
        elif values:
            conflicts[key] = {value: sorted(sources) for value, sources in sorted(values.items())}

    args.output.parent.mkdir(parents=True, exist_ok=True)
    before = Counter()
    after = Counter()
    filled = Counter()
    replaced = Counter()
    exact_matches = Counter()
    unmatched_corrections = set(unique)
    rows = 0
    with args.input.open(newline="", encoding="utf-8") as source, args.output.open("w", newline="", encoding="utf-8") as target:
        reader = csv.DictReader(source)
        if list(reader.fieldnames or []) != OUTPUT_FIELDS:
            raise RuntimeError("Unexpected normalized input schema")
        writer = csv.DictWriter(target, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in reader:
            rows += 1
            base_key = (
                row["archive_id"], row["adsh"], row["observation_date"],
                clean_member(row["investment_identifier"]),
            )
            source_concepts = json.loads(row.get("source_concepts_json") or "{}")
            for field in FIELDS:
                if row.get(field) and row[field] != "UNKNOWN":
                    before[field] += 1
                correction_key = (base_key, field)
                correction = unique.get(correction_key)
                if correction:
                    unmatched_corrections.discard(correction_key)
                    value, sources = correction
                    exact_matches[field] += 1
                    old = row.get(field, "")
                    if old in {"", "UNKNOWN", "unknown"}:
                        row[field] = value
                        filled[field] += 1
                    elif field == "reference_rate" and old != value:
                        row[field] = value
                        replaced[field] += 1
                    source_concepts[f"{field}_lineage_v2"] = "|".join(sources)
                if row.get(field) and row[field] != "UNKNOWN":
                    after[field] += 1
            row["source_concepts_json"] = canonical_json(source_concepts)
            writer.writerow(row)

    metadata = {
        "schema_version": "lineage_v2",
        "input_sha256": sha256_file(args.input),
        "output_sha256": sha256_file(args.output),
        "rows": rows,
        "official_sources_only": True,
        "identifier_text_used_to_infer_fields": False,
        "exact_join_key": ["archive_id", "adsh", "observation_date", "Investment Identifier Axis member"],
        "coverage_before": dict(before),
        "coverage_after": dict(after),
        "filled_missing": dict(filled),
        "replaced_inferred_reference_rate": dict(replaced),
        "exact_support_or_direct_matches": dict(exact_matches),
        "ambiguous_field_keys_not_applied": len(conflicts),
        "unmatched_unique_correction_keys": len(unmatched_corrections),
        "conflict_examples": [
            {"key": list(key[0]) + [key[1]], "values": values}
            for key, values in list(sorted(conflicts.items(), key=lambda item: str(item[0])))[:10]
        ],
        "storage": "corrected normalized CSV cached outside Git; metadata and checksums committed",
    }
    write_json(args.metadata, metadata)
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Audit official SEC BDC field lineage without parsing identifier prose.

The audit is intentionally diagnostic.  It inventories the wide SOI table and
supporting XBRL fact tables, then traces four matcher fields through the
normalized, aggregated, and public blind-export stages.
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
sys.path.insert(0, str(DAY2))

from common import (  # noqa: E402
    canonical_json, clean_member, decimal_or_none, iso_date_or_blank, read_csv,
    sha256_file, write_csv, write_json,
)

csv.field_size_limit(sys.maxsize)


FIELDS = ("maturity", "currency", "reference_rate", "acquisition_date")
STAGES = ("raw_soi", "supporting_facts", "normalized", "aggregated", "blind_export")
DIRECT_COLUMNS = {
    "maturity": ("Investment Maturity Date", "Derivative, Contract End Date"),
    "currency": ("Currency Axis", "Derivative, Currency Bought"),
    "reference_rate": (
        "RateType",
        "Variable Rate Axis",
        "InterestRatePeriod",
        "InterestType",
        "Investment, Variable Interest Rate, Type [Extensible Enumeration]",
        "Debt Instrument, Interest Rate Terms",
    ),
    "acquisition_date": ("Investment, Acquisition Date", "Award Date Axis"),
}
MISSING_SENTINELS = {"", "unknown", "none", "null", "n/a", "na"}
VALUE_COLUMNS = {
    "principal": (
        "Investment Owned, Balance, Principal Amount", "Investment Owned, Face Amount",
        "Debt Securities, Available-for-Sale, Amortized Cost",
    ),
    "cost": (
        "Adjusted cost basis", "Investment Owned, Cost",
        "Debt Securities, Trading, and Equity Securities, FV-NI, Cost",
        "Debt Securities, Available-for-Sale, Amortized Cost",
    ),
    "fair_value": (
        "Initial fair value of Investment", "Investment Owned, Fair Value",
        "Investments, Fair Value Disclosure", "Debt Securities, Held-to-Maturity, Fair Value",
    ),
}

OUTPUT_FIELDS = [
    "field", "stage", "archive", "fund", "cik", "source_table",
    "source_column_or_concept", "raw_row_count", "non_missing_count",
    "non_missing_percentage", "normalized_row_count",
    "normalized_non_missing_count", "normalized_coverage",
    "aggregated_row_count", "aggregated_non_missing_count",
    "aggregated_coverage", "blind_row_count", "blind_non_missing_count",
    "blind_coverage", "aggregation_loss_count", "export_loss_count",
    "direct_parser_loss_count", "support_join_loss_count", "support_unmatched_count",
    "exact_loss_stage", "representative_raw_examples_json", "diagnosis",
    "recommended_action",
]


def present(value):
    return str(value or "").strip().lower() not in MISSING_SENTINELS


def pct(numerator, denominator):
    return "" if not denominator else f"{100.0 * numerator / denominator:.6f}"


def clean_value(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def sec_date(value):
    value = str(value or "").strip()
    if re.fullmatch(r"\d{8}", value):
        value = f"{value[:4]}-{value[4:6]}-{value[6:]}"
    return iso_date_or_blank(value)


def extract_investment_member(segments):
    """Return an explicitly tagged investment member, never inferred prose."""
    preferred = []
    fallback = []
    for segment in str(segments or "").split(";"):
        axis, separator, member = segment.partition("=")
        if not separator:
            continue
        axis_name = axis.split("(", 1)[0].lower()
        member = clean_member(re.sub(r"\(\);?$", "", member).strip())
        if not member:
            continue
        if "investmentidentifieraxis" in axis_name:
            preferred.append(member)
        elif any(token in axis_name for token in (
            "investmentnameaxis", "investmentissuernameaxis", "portfoliocompanies",
        )):
            fallback.append(member)
    values = preferred or fallback
    return values[0] if values else ""


def currency_members(segments):
    values = []
    for segment in str(segments or "").split(";"):
        axis, separator, member = segment.partition("=")
        if not separator or "currencyaxis" not in axis.lower():
            continue
        member = re.sub(r"\(\);?$", "", member).strip()
        if member:
            values.append(member)
    return values


def semantic_field(tag, label, doc):
    tag_l = str(tag or "").lower()
    label_l = str(label or "").lower()
    text = " ".join((str(label or ""), str(doc or ""))).lower()
    if (
        "investmentduedate" in tag_l
        or "investmentmaturitydate" in tag_l
        or ("investment" in text and ("maturity date" in text or "due date" in text))
    ):
        return "maturity"
    if (
        "initialacquisitiondate" in tag_l
        or tag_l == "acquisitiondate"
        or ("investment" in text and "acquisition date" in text)
    ):
        return "acquisition_date"
    if (
        "investmentreferencerate" in tag_l
        or "referencerateandspread" in tag_l
        or ("investment" in label_l and "reference rate" in label_l)
    ):
        return "reference_rate"
    return ""


def load_universe(path):
    universe = {}
    for row in read_csv(path):
        cik = str(int(row["cik"]))
        universe[cik] = row["ticker"]
    if len(universe) != 19:
        raise RuntimeError(f"Expected 19 BDC CIKs, found {len(universe)}")
    return universe


def load_manifest(path):
    rows = read_csv(path)
    if len(rows) != 8:
        raise RuntimeError(f"Expected 8 SEC archives, found {len(rows)}")
    return rows


def archive_path(cache_dir, manifest_row):
    filename = Path(urllib.parse.urlparse(manifest_row["source_url"]).path).name
    path = cache_dir / filename
    if not path.exists():
        raise FileNotFoundError(path)
    if sha256_file(path) != manifest_row["sha256"]:
        raise RuntimeError(f"Checksum mismatch: {path}")
    return path


def read_archive_submissions(archive, member, universe):
    by_adsh = {}
    with archive.open(member) as raw:
        reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""), delimiter="\t")
        for row in reader:
            cik = str(int(row["cik"])) if row.get("cik") else ""
            if cik in universe and row.get("form") in {"10-Q", "10-K"}:
                by_adsh[row["adsh"]] = (universe[cik], cik)
    return by_adsh


def add_example(store, key, example):
    if len(store[key]) < 10:
        store[key].append(example)


def normalized_lookup(rows_by_id):
    lookup = defaultdict(list)
    for row in rows_by_id.values():
        key = (
            row["archive_id"], row["adsh"], row["observation_date"],
            clean_member(row["investment_identifier"]),
        )
        lookup[key].append(row)
    return lookup


def facility_like_soi_row(row):
    if not clean_member(row.get("Investment, Identifier Axis", "")):
        return False
    numeric = []
    for columns in VALUE_COLUMNS.values():
        value = next((row.get(column, "") for column in columns if present(row.get(column))), "")
        numeric.append(decimal_or_none(value))
    return sum(value is not None for value in numeric) >= 2


def inspect_archive(path, manifest_row, universe, normalized_rows):
    direct_total = Counter()
    direct_values = Counter()
    direct_concepts = defaultdict(Counter)
    support_values = Counter()
    support_concepts = defaultdict(Counter)
    direct_parser_losses = Counter()
    support_join_losses = Counter()
    support_unmatched = Counter()
    direct_examples = defaultdict(list)
    support_examples = defaultdict(list)
    inventory = []

    with zipfile.ZipFile(path) as archive:
        inventory = sorted(archive.namelist())
        required = {
            "soi.tsv", "datasets/sub.tsv", "datasets/tag.tsv", "datasets/num.tsv",
            "datasets/txt.tsv", "datasets/non.tsv", "datasets/cal.tsv", "datasets/pre.tsv",
            "bdc_metadata.json", "readme.htm",
        }
        if set(inventory) != required:
            raise RuntimeError(f"Unexpected ZIP inventory for {manifest_row['archive_id']}: {inventory}")

        submissions = read_archive_submissions(archive, manifest_row["submission_member"], universe)

        with archive.open(manifest_row["soi_member"]) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""), delimiter="\t")
            headers = set(reader.fieldnames or [])
            for columns in DIRECT_COLUMNS.values():
                if not any(column in headers for column in columns):
                    raise RuntimeError(f"SOI schema lacks all expected columns: {columns}")
            for line_number, row in enumerate(reader, start=2):
                identity = submissions.get(row.get("adsh", ""))
                if not identity:
                    continue
                if not facility_like_soi_row(row):
                    continue
                ticker, cik = identity
                identifier = clean_member(row.get("Investment, Identifier Axis", ""))
                row_key = (
                    manifest_row["archive_id"], row["adsh"], sec_date(row.get("ddate")), identifier,
                )
                normalized_matches = normalized_rows.get(row_key, [])
                for field, columns in DIRECT_COLUMNS.items():
                    key = (ticker, cik, field)
                    direct_total[key] += 1
                    for column in columns:
                        value = clean_value(row.get(column))
                        if not present(value):
                            continue
                        direct_values[key] += 1
                        direct_concepts[key][f"soi.tsv:{column}"] += 1
                        if normalized_matches and not any(present(match.get(field)) for match in normalized_matches):
                            direct_parser_losses[key] += 1
                        add_example(direct_examples, key, {
                            "table": "soi.tsv", "line": line_number, "adsh": row["adsh"],
                            "concept": column, "value": value,
                            "investment_identifier": identifier,
                        })

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
                    identity = submissions.get(row.get("adsh", ""))
                    if not identity:
                        continue
                    ticker, cik = identity
                    member = extract_investment_member(row.get("segments"))
                    if not member:
                        continue
                    key_pair = (row.get("tag", ""), row.get("version", ""))
                    field = tag_fields.get(key_pair, "")
                    if field and present(row.get("value")):
                        key = (ticker, cik, field)
                        support_values[key] += 1
                        support_concepts[key][f"{table}:{row['tag']}@{row['version']}"] += 1
                        add_example(support_examples, key, {
                            "table": table, "line": line_number, "adsh": row["adsh"],
                            "concept": row["tag"], "version": row["version"],
                            "value": clean_value(row.get("value")),
                            "investment_member": clean_value(member),
                        })
                        support_key = (
                            manifest_row["archive_id"], row["adsh"],
                            sec_date(row.get("ddate")), clean_member(member),
                        )
                        normalized_matches = normalized_rows.get(support_key, [])
                        if not normalized_matches:
                            support_unmatched[key] += 1
                        elif not any(present(match.get(field)) for match in normalized_matches):
                            support_join_losses[key] += 1
                    for value in currency_members(row.get("segments")):
                        key = (ticker, cik, "currency")
                        support_values[key] += 1
                        support_concepts[key][f"{table}:CurrencyAxis"] += 1
                        add_example(support_examples, key, {
                            "table": table, "line": line_number, "adsh": row["adsh"],
                            "concept": "CurrencyAxis", "value": clean_value(value),
                            "investment_member": clean_value(member),
                        })

    return {
        "direct_total": direct_total,
        "direct_values": direct_values,
        "direct_concepts": direct_concepts,
        "support_values": support_values,
        "support_concepts": support_concepts,
        "direct_parser_losses": direct_parser_losses,
        "support_join_losses": support_join_losses,
        "support_unmatched": support_unmatched,
        "direct_examples": direct_examples,
        "support_examples": support_examples,
        "inventory": inventory,
    }


def scan_stage_csv(path, key_fields=("archive_id", "ticker")):
    totals = Counter()
    values = Counter()
    rows_by_id = {}
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            archive = row[key_fields[0]]
            ticker = row[key_fields[1]]
            totals[(archive, ticker)] += 1
            for field in FIELDS:
                if present(row.get(field)):
                    values[(archive, ticker, field)] += 1
            if row.get("facility_row_id"):
                rows_by_id[row["facility_row_id"]] = row
    return totals, values, rows_by_id


def trace_aggregation_losses(normalized_by_id, aggregated_path):
    losses = Counter()
    with Path(aggregated_path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            source_ids = json.loads(row.get("source_row_ids_json") or "[]")
            for field in FIELDS:
                source_present = any(
                    source_id in normalized_by_id and present(normalized_by_id[source_id].get(field))
                    for source_id in source_ids
                )
                if source_present and not present(row.get(field)):
                    losses[(row["archive_id"], row["ticker"], field)] += 1
    return losses


def blind_counts(blind_path, aggregate_rows):
    lookup = defaultdict(list)
    for row in aggregate_rows.values():
        if row.get("is_current_period") == "True":
            lookup[(row["period_end"], row["ticker"], row["investment_identifier"], row["borrower_norm"])].append(row)
    totals = Counter()
    values = Counter()
    export_losses = Counter()
    with Path(blind_path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            for side in ("left", "right"):
                key = (
                    row["period_end"], row[f"{side}_ticker"], row[f"{side}_identifier"],
                    row[f"{side}_borrower_norm"],
                )
                matches = lookup.get(key, [])
                archive = matches[0]["archive_id"] if matches else "unresolved"
                ticker = row[f"{side}_ticker"]
                totals[(archive, ticker)] += 1
                for field in FIELDS:
                    blind_value = row.get(f"{side}_{field}", "")
                    if present(blind_value):
                        values[(archive, ticker, field)] += 1
                    aggregate_present = {present(match.get(field)) for match in matches}
                    if aggregate_present == {True} and not present(blind_value):
                        export_losses[(archive, ticker, field)] += 1
    return totals, values, export_losses


def global_diagnosis(
    field, raw_direct, raw_support, normalized, aggregation_loss, export_loss,
    direct_parser_loss, support_join_loss,
):
    if raw_direct + raw_support == 0:
        return "source_absent", "official_source", (
            "Treat the field as unavailable in the inspected free SEC archives; use abstention."
        )
    if export_loss:
        return "export_loss", "blind_export", "Repair export and supersede the blind benchmark."
    if aggregation_loss:
        return "aggregation_loss", "economic_aggregation", "Repair aggregation and supersede the blind benchmark."
    if direct_parser_loss:
        return "parser_loss", "raw_soi_to_normalized", "Repair direct SOI parsing and supersede the blind benchmark."
    if support_join_loss:
        return "join_loss", "supporting_facts_to_normalized", (
            "Join explicitly tagged supporting facts to SOI rows and supersede the blind benchmark."
        )
    return "source_absent", "source_coverage_ceiling", (
        "No processing loss detected; missing blind values reflect source coverage for sampled facilities."
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("data/day3/sec_bdc_raw_manifest.csv"))
    parser.add_argument("--cache-dir", type=Path, default=Path("/private/tmp/finance-day3-sec-cache"))
    parser.add_argument("--reporting-order", type=Path, default=Path("data/day3/reporting_order_extended.csv"))
    parser.add_argument("--normalized", type=Path, default=Path("/private/tmp/finance-day3-sec-cache/bdc_soi_normalized.csv"))
    parser.add_argument("--aggregated", type=Path, default=Path("/private/tmp/finance-day3-sec-cache/bdc_facilities_agg.csv"))
    parser.add_argument("--blind", type=Path, default=Path("data/day3/blind_facility_pairs_v2.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/day3/field_lineage_audit.csv"))
    parser.add_argument("--summary", type=Path, default=Path("data/day3/field_lineage_audit_summary.json"))
    args = parser.parse_args()

    universe = load_universe(args.reporting_order)
    manifest = load_manifest(args.manifest)
    norm_total, norm_values, normalized_by_id = scan_stage_csv(args.normalized)
    normalized_rows = normalized_lookup(normalized_by_id)
    archive_results = {}
    for manifest_row in manifest:
        path = archive_path(args.cache_dir, manifest_row)
        archive_results[manifest_row["archive_id"]] = inspect_archive(
            path, manifest_row, universe, normalized_rows,
        )
        print(f"lineage raw scan: {manifest_row['archive_id']}", flush=True)

    agg_total, agg_values, aggregated_by_id = scan_stage_csv(args.aggregated)
    aggregation_losses = trace_aggregation_losses(normalized_by_id, args.aggregated)
    blind_total, blind_values, export_losses = blind_counts(args.blind, aggregated_by_id)

    global_counts = {field: Counter() for field in FIELDS}
    for archive_id, result in archive_results.items():
        for ticker, cik in sorted((ticker, cik) for cik, ticker in universe.items()):
            for field in FIELDS:
                key = (ticker, cik, field)
                global_counts[field]["raw_direct"] += result["direct_values"][key]
                global_counts[field]["raw_support"] += result["support_values"][key]
                global_counts[field]["normalized"] += norm_values[(archive_id, ticker, field)]
                global_counts[field]["aggregated"] += agg_values[(archive_id, ticker, field)]
                global_counts[field]["blind"] += blind_values[(archive_id, ticker, field)]
                global_counts[field]["aggregation_loss"] += aggregation_losses[(archive_id, ticker, field)]
                global_counts[field]["export_loss"] += export_losses[(archive_id, ticker, field)]
                global_counts[field]["direct_parser_loss"] += result["direct_parser_losses"][key]
                global_counts[field]["support_join_loss"] += result["support_join_losses"][key]
                global_counts[field]["support_unmatched"] += result["support_unmatched"][key]

    diagnoses = {}
    for field, counts in global_counts.items():
        diagnosis, loss_stage, action = global_diagnosis(
            field, counts["raw_direct"], counts["raw_support"], counts["normalized"],
            counts["aggregation_loss"], counts["export_loss"],
            counts["direct_parser_loss"], counts["support_join_loss"],
        )
        diagnoses[field] = {"diagnosis": diagnosis, "exact_loss_stage": loss_stage, "recommended_action": action}

    output = []
    for archive_id, result in archive_results.items():
        for cik, ticker in sorted(universe.items(), key=lambda item: item[1]):
            for field in FIELDS:
                key = (ticker, cik, field)
                raw_total = result["direct_total"][key]
                raw_direct = result["direct_values"][key]
                support = result["support_values"][key]
                n_total = norm_total[(archive_id, ticker)]
                n_values = norm_values[(archive_id, ticker, field)]
                a_total = agg_total[(archive_id, ticker)]
                a_values = agg_values[(archive_id, ticker, field)]
                b_total = blind_total[(archive_id, ticker)]
                b_values = blind_values[(archive_id, ticker, field)]
                chain = {
                    "normalized_row_count": n_total,
                    "normalized_non_missing_count": n_values,
                    "normalized_coverage": pct(n_values, n_total),
                    "aggregated_row_count": a_total,
                    "aggregated_non_missing_count": a_values,
                    "aggregated_coverage": pct(a_values, a_total),
                    "blind_row_count": b_total,
                    "blind_non_missing_count": b_values,
                    "blind_coverage": pct(b_values, b_total),
                    "aggregation_loss_count": aggregation_losses[(archive_id, ticker, field)],
                    "export_loss_count": export_losses[(archive_id, ticker, field)],
                    "direct_parser_loss_count": result["direct_parser_losses"][key],
                    "support_join_loss_count": result["support_join_losses"][key],
                    "support_unmatched_count": result["support_unmatched"][key],
                    "exact_loss_stage": diagnoses[field]["exact_loss_stage"],
                    "diagnosis": diagnoses[field]["diagnosis"],
                    "recommended_action": diagnoses[field]["recommended_action"],
                }
                stage_values = {
                    "raw_soi": (raw_total, raw_direct, "soi.tsv", result["direct_concepts"][key]),
                    "supporting_facts": (raw_total, support, "datasets/num.tsv|datasets/txt.tsv|datasets/non.tsv", result["support_concepts"][key]),
                    "normalized": (n_total, n_values, str(args.normalized), Counter({field: n_values}) if n_values else Counter()),
                    "aggregated": (a_total, a_values, str(args.aggregated), Counter({field: a_values}) if a_values else Counter()),
                    "blind_export": (b_total, b_values, str(args.blind), Counter({f"left/right_{field}": b_values}) if b_values else Counter()),
                }
                for stage in STAGES:
                    denominator, non_missing, source_table, concepts = stage_values[stage]
                    if stage == "raw_soi":
                        stage_examples = result["direct_examples"][key]
                    elif stage == "supporting_facts":
                        stage_examples = result["support_examples"][key]
                    else:
                        stage_examples = []
                    output.append({
                        "field": field, "stage": stage, "archive": archive_id,
                        "fund": ticker, "cik": cik, "source_table": source_table,
                        "source_column_or_concept": canonical_json(dict(concepts)),
                        "raw_row_count": denominator,
                        "non_missing_count": non_missing,
                        "non_missing_percentage": pct(non_missing, denominator),
                        "representative_raw_examples_json": canonical_json(stage_examples),
                        **chain,
                    })

    write_csv(args.output, output, OUTPUT_FIELDS)
    rebuild = any(item["diagnosis"] in {"parser_loss", "join_loss", "aggregation_loss", "export_loss"} for item in diagnoses.values())
    summary = {
        "audit_scope": {
            "archives": [row["archive_id"] for row in manifest],
            "archive_count": len(manifest),
            "fund_count": len(universe),
            "fields": list(FIELDS),
            "zip_inventory_verified": {archive: result["inventory"] for archive, result in archive_results.items()},
            "identifier_text_used_to_infer_fields": False,
        },
        "input_hashes": {
            "manifest": sha256_file(args.manifest), "normalized": sha256_file(args.normalized),
            "aggregated": sha256_file(args.aggregated), "blind": sha256_file(args.blind),
        },
        "fields": {
            field: {**dict(global_counts[field]), **diagnoses[field]}
            for field in FIELDS
        },
        "pipeline_loss_found": rebuild,
        "conditional_action": "rebuild_blind_v3" if rebuild else "retain_blind_v2_source_ceiling",
        "output_sha256": "populated_after_write",
    }
    summary["output_sha256"] = sha256_file(args.output)
    write_json(args.summary, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

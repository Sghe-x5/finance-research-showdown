#!/usr/bin/env python3
"""Aggregate XBRL investment slices to one BDC economic facility per quarter."""

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

DAY2 = Path(__file__).resolve().parents[1] / "day2"
sys.path.insert(0, str(DAY2))

from common import (  # noqa: E402
    canonical_json, decimal_or_none, read_csv, sha256_bytes, sha256_file,
    stable_id, write_csv, write_json,
)


DEFAULT_INPUT = Path("/private/tmp/finance-day3-sec-cache/bdc_soi_normalized.csv")
DEFAULT_OUTPUT = Path("/private/tmp/finance-day3-sec-cache/bdc_facilities_agg.csv")
DEFAULT_METADATA = Path("data/day3/bdc_facilities_agg_metadata.json")

FIELDS = [
    "facility_row_id", "economic_facility_id", "archive_id", "adsh", "accepted",
    "cik", "ticker", "filer_name", "form", "filed", "period_end",
    "observation_date", "is_current_period", "investment_identifier",
    "borrower_raw", "borrower_norm", "debt_equity", "facility_type", "lien",
    "currency", "reference_rate", "spread", "spread_bucket_25bp",
    "total_interest_rate", "pik_rate", "maturity", "maturity_month",
    "funded_status", "acquisition_date", "principal", "cost", "fair_value",
    "mark_fv_to_principal", "non_accrual", "restructuring_flag",
    "issuer_affiliation", "lot_count", "source_row_count", "source_row_ids_sha256",
    "source_row_ids_json", "raw_provenance_json", "aggregation_rule_version",
]


def number(value):
    parsed = decimal_or_none(value)
    return 0.0 if parsed is None else parsed


def fmt_number(value):
    if value is None:
        return ""
    return f"{value:.10f}".rstrip("0").rstrip(".")


def spread_bucket(value, width=0.0025):
    value = decimal_or_none(value)
    if value is None:
        return ""
    return fmt_number(round(value / width) * width)


def maturity_month(value):
    try:
        parsed = date.fromisoformat((value or "")[:10])
    except ValueError:
        return ""
    return f"{parsed.year:04d}-{parsed.month:02d}"


def weighted_average(rows, field):
    values = []
    for row in rows:
        value = decimal_or_none(row.get(field))
        if value is None:
            continue
        weight = abs(number(row.get("principal"))) or abs(number(row.get("cost"))) or 1.0
        values.append((value, weight))
    if not values:
        return None
    denominator = sum(weight for _, weight in values)
    return sum(value * weight for value, weight in values) / denominator


def facility_key(row):
    return (
        row["adsh"], row["observation_date"], row["borrower_norm"],
        row["debt_equity"], row["facility_type"], row["lien"], row["currency"],
        row["reference_rate"], spread_bucket(row["spread"]),
        maturity_month(row["maturity"]), row["funded_status"],
    )


def should_drop_issuer_total(row, borrower_group):
    """Drop borrower totals that would double-count principal-bearing debt lots."""
    if decimal_or_none(row.get("principal")) is not None:
        return False
    if row.get("funded_status") == "unfunded":
        return False
    if row.get("debt_equity") == "equity":
        return False
    has_principal_detail = any(decimal_or_none(other.get("principal")) is not None for other in borrower_group)
    is_unspecified = (
        row.get("facility_type") in {"", "unknown", "other_debt"}
        and row.get("lien") in {"", "unknown"}
        and row.get("reference_rate") in {"", "UNKNOWN"}
        and not row.get("spread")
        and not row.get("maturity")
    )
    return has_principal_detail and is_unspecified


def deduplicate_lots(rows):
    seen = set()
    output = []
    for row in sorted(rows, key=lambda item: item["facility_row_id"]):
        signature = (
            row["investment_identifier"], row["principal"], row["cost"], row["fair_value"],
            row["spread"], row["maturity"], row["funded_status"], row["acquisition_date"],
        )
        if signature in seen:
            continue
        seen.add(signature)
        output.append(row)
    return output


def aggregate_group(rows):
    rows = deduplicate_lots(rows)
    first = rows[0]
    source_ids = sorted(row["facility_row_id"] for row in rows)
    identifiers = sorted({row["investment_identifier"] for row in rows})
    raw_names = sorted({row["borrower_raw"] for row in rows})
    provenance = sorted({row["raw_provenance"] for row in rows})
    principal_values = [decimal_or_none(row["principal"]) for row in rows]
    principal = sum(value for value in principal_values if value is not None)
    has_principal = any(value is not None for value in principal_values)
    cost_values = [decimal_or_none(row["cost"]) for row in rows]
    fair_values = [decimal_or_none(row["fair_value"]) for row in rows]
    cost = sum(value for value in cost_values if value is not None)
    fair_value = sum(value for value in fair_values if value is not None)
    has_cost = any(value is not None for value in cost_values)
    has_fair_value = any(value is not None for value in fair_values)
    key = facility_key(first)
    economic_id = "EF_" + stable_id(*key, length=28)
    mark = None if not has_principal or principal == 0 or not has_fair_value else fair_value / principal
    return {
        "facility_row_id": economic_id,
        "economic_facility_id": economic_id,
        "archive_id": first["archive_id"],
        "adsh": first["adsh"],
        "accepted": max(row["accepted"] for row in rows),
        "cik": first["cik"],
        "ticker": first["ticker"],
        "filer_name": first["filer_name"],
        "form": first["form"],
        "filed": first["filed"],
        "period_end": first["period_end"],
        "observation_date": first["observation_date"],
        "is_current_period": str(first["period_end"] == first["observation_date"]),
        "investment_identifier": " | ".join(identifiers),
        "borrower_raw": " | ".join(raw_names),
        "borrower_norm": first["borrower_norm"],
        "debt_equity": first["debt_equity"],
        "facility_type": first["facility_type"],
        "lien": first["lien"],
        "currency": first["currency"],
        "reference_rate": first["reference_rate"],
        "spread": fmt_number(weighted_average(rows, "spread")),
        "spread_bucket_25bp": spread_bucket(first["spread"]),
        "total_interest_rate": fmt_number(weighted_average(rows, "total_interest_rate")),
        "pik_rate": fmt_number(weighted_average(rows, "pik_rate")),
        "maturity": min((row["maturity"] for row in rows if row["maturity"]), default=""),
        "maturity_month": maturity_month(first["maturity"]),
        "funded_status": first["funded_status"],
        "acquisition_date": min((row["acquisition_date"] for row in rows if row["acquisition_date"]), default=""),
        "principal": fmt_number(principal) if has_principal else "",
        "cost": fmt_number(cost) if has_cost else "",
        "fair_value": fmt_number(fair_value) if has_fair_value else "",
        "mark_fv_to_principal": fmt_number(mark),
        "non_accrual": str(any(row["non_accrual"] == "True" for row in rows)),
        "restructuring_flag": str(any(row["restructuring_flag"] == "True" for row in rows)),
        "issuer_affiliation": " | ".join(sorted({row["issuer_affiliation"] for row in rows if row["issuer_affiliation"]})),
        "lot_count": len(identifiers),
        "source_row_count": len(rows),
        "source_row_ids_sha256": sha256_bytes(canonical_json(source_ids).encode("utf-8")),
        "source_row_ids_json": canonical_json(source_ids),
        "raw_provenance_json": canonical_json(provenance),
        "aggregation_rule_version": "economic_facility_v1",
    }


def aggregate(rows):
    borrower_groups = defaultdict(list)
    for row in rows:
        if not row["borrower_norm"]:
            continue
        borrower_groups[(row["adsh"], row["observation_date"], row["borrower_norm"])].append(row)

    retained = []
    dropped = []
    for values in borrower_groups.values():
        for row in values:
            if should_drop_issuer_total(row, values):
                dropped.append(row)
            else:
                retained.append(row)

    groups = defaultdict(list)
    for row in retained:
        groups[facility_key(row)].append(row)
    facilities = [aggregate_group(values) for _, values in sorted(groups.items())]
    facilities.sort(key=lambda row: (row["period_end"], row["ticker"], row["economic_facility_id"]))
    return facilities, dropped


def validate(facilities):
    ids = [row["economic_facility_id"] for row in facilities]
    if len(ids) != len(set(ids)):
        raise RuntimeError("Economic-facility IDs are not unique")
    for row in facilities:
        for field in ("principal", "cost", "fair_value", "mark_fv_to_principal"):
            value = decimal_or_none(row[field])
            if value is not None and not math.isfinite(value):
                raise RuntimeError(f"Non-finite {field} for {row['economic_facility_id']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    args = parser.parse_args()
    rows = read_csv(args.input)
    facilities, dropped = aggregate(rows)
    validate(facilities)
    write_csv(args.output, facilities, FIELDS)
    metadata = {
        "aggregation_rule_version": "economic_facility_v1",
        "input_sha256": sha256_file(args.input),
        "output_sha256": sha256_file(args.output),
        "normalized_input_rows": len(rows),
        "issuer_total_rows_dropped_to_avoid_double_counting": len(dropped),
        "economic_facility_rows": len(facilities),
        "current_period_facility_rows": sum(row["is_current_period"] == "True" for row in facilities),
        "position_periods": dict(sorted(Counter(row["period_end"] for row in facilities if row["is_current_period"] == "True").items())),
        "lot_count_distribution": dict(sorted(Counter(row["lot_count"] for row in facilities).items(), key=lambda item: int(item[0]))),
        "storage": "aggregated facility CSV cached outside Git; metadata and checksums committed",
        "grouping": [
            "BDC accession", "observation date", "normalized borrower", "debt/equity",
            "facility type", "lien", "currency", "reference-rate family",
            "25bp spread bucket", "maturity month", "funded status",
        ],
    }
    write_json(args.metadata, metadata)
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

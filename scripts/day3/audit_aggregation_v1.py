#!/usr/bin/env python3
"""Lock review samples for economic_facility_v1 before replacing its grouping key."""

import argparse
import json
import random
import re
import sys
from pathlib import Path

DAY2 = Path(__file__).resolve().parents[1] / "day2"
sys.path.insert(0, str(DAY2))

from common import SEED, canonical_json, decimal_or_none, normalize_text, read_csv, sha256_bytes, sha256_file, write_csv, write_json  # noqa: E402


DEFAULT_RAW = Path("/private/tmp/finance-day3-sec-cache/bdc_soi_normalized.csv")
DEFAULT_V1 = Path("/private/tmp/finance-day3-sec-cache/bdc_facilities_agg.csv")
DEFAULT_MULTILOT = Path("data/day3/aggregation_v1_multilot_review.csv")
DEFAULT_DROPPED = Path("data/day3/aggregation_v1_issuer_total_review.csv")
DEFAULT_META = Path("data/day3/aggregation_v1_audit_meta.json")

MULTILOT_FIELDS = [
    "review_group_id", "v1_economic_facility_id", "ticker", "period_end",
    "observation_date", "borrower_norm", "lot_count", "source_row_count",
    "raw_identifiers_json", "raw_row_ids_json", "v1_spreads_json",
    "v1_maturities_json", "v1_facility_types_json", "v1_liens_json",
    "proposed_v2_key_count", "proposed_v2_keys_sha256",
    "auto_v1_merges_multiple_v2_groups", "proposed_grouping",
    "manual_same_economic_facility", "review_notes",
]

DROPPED_FIELDS = [
    "review_row_id", "facility_row_id", "ticker", "period_end",
    "observation_date", "borrower_norm", "raw_identifier", "debt_equity",
    "facility_type", "lien", "currency", "reference_rate", "spread",
    "maturity", "funded_status", "principal", "cost", "fair_value",
    "sibling_identifiers_json", "principal_detail_sibling_count",
    "proposed_drop_reason", "manual_should_drop_as_issuer_total", "review_notes",
]


def exact_number(value):
    parsed = decimal_or_none(value)
    if parsed is None:
        return "UNKNOWN"
    return f"{parsed:.12f}".rstrip("0").rstrip(".")


def canonical_tranche_text(row):
    identifier = normalize_text(row.get("investment_identifier", ""))
    borrower_tokens = set(normalize_text(row.get("borrower_norm", "")).split())
    legal_suffixes = {"llc", "inc", "corp", "corporation", "company", "co", "lp", "ltd"}
    tokens = [
        token for token in identifier.split()
        if token not in borrower_tokens and token not in legal_suffixes
    ]
    text = " ".join(tokens).strip()
    return text or f"ROW:{row['facility_row_id']}"


def proposed_v2_key(row):
    return (
        row["adsh"], row["observation_date"], row["borrower_norm"],
        row["debt_equity"], row["facility_type"], row["lien"], row["currency"],
        row["reference_rate"], exact_number(row.get("spread")),
        row.get("maturity") or "UNKNOWN", row["funded_status"],
        canonical_tranche_text(row),
    )


def should_drop_issuer_total(row, borrower_group):
    if decimal_or_none(row.get("principal")) is not None:
        return False
    if row.get("funded_status") == "unfunded" or row.get("debt_equity") == "equity":
        return False
    has_principal_detail = any(decimal_or_none(other.get("principal")) is not None for other in borrower_group)
    is_unspecified = (
        row.get("facility_type") in {"", "unknown", "other_debt"}
        and row.get("lien") in {"", "unknown"}
        and row.get("reference_rate") in {"", "UNKNOWN"}
        and not row.get("spread") and not row.get("maturity")
    )
    return has_principal_detail and is_unspecified


def sample_multilot(v1_rows, raw_by_id, sample_size, seed):
    candidates = [row for row in v1_rows if int(row.get("lot_count") or 0) > 1]
    if len(candidates) < sample_size:
        raise RuntimeError(f"Need {sample_size} v1 multi-lot groups, found {len(candidates)}")
    selected = random.Random(seed).sample(sorted(candidates, key=lambda row: row["economic_facility_id"]), sample_size)
    output = []
    for group in sorted(selected, key=lambda row: row["economic_facility_id"]):
        source_ids = json.loads(group["source_row_ids_json"])
        raw_rows = [raw_by_id[row_id] for row_id in source_ids]
        v2_keys = sorted({canonical_json(proposed_v2_key(row)) for row in raw_rows})
        output.append({
            "review_group_id": "AGG_MULTI_" + sha256_bytes(group["economic_facility_id"].encode("utf-8"))[:16],
            "v1_economic_facility_id": group["economic_facility_id"],
            "ticker": group["ticker"],
            "period_end": group["period_end"],
            "observation_date": group["observation_date"],
            "borrower_norm": group["borrower_norm"],
            "lot_count": group["lot_count"],
            "source_row_count": group["source_row_count"],
            "raw_identifiers_json": canonical_json(sorted(row["investment_identifier"] for row in raw_rows)),
            "raw_row_ids_json": canonical_json(sorted(source_ids)),
            "v1_spreads_json": canonical_json(sorted({row["spread"] or "UNKNOWN" for row in raw_rows})),
            "v1_maturities_json": canonical_json(sorted({row["maturity"] or "UNKNOWN" for row in raw_rows})),
            "v1_facility_types_json": canonical_json(sorted({row["facility_type"] for row in raw_rows})),
            "v1_liens_json": canonical_json(sorted({row["lien"] for row in raw_rows})),
            "proposed_v2_key_count": len(v2_keys),
            "proposed_v2_keys_sha256": sha256_bytes(canonical_json(v2_keys).encode("utf-8")),
            "auto_v1_merges_multiple_v2_groups": str(len(v2_keys) > 1),
            "proposed_grouping": "split by exact spread, exact maturity and canonical tranche text",
            "manual_same_economic_facility": "",
            "review_notes": "",
        })
    return output, len(candidates)


def sample_dropped(raw_rows, sample_size, seed):
    borrower_groups = {}
    for row in raw_rows:
        key = (row["adsh"], row["observation_date"], row["borrower_norm"])
        borrower_groups.setdefault(key, []).append(row)
    dropped = []
    for group in borrower_groups.values():
        for row in group:
            if should_drop_issuer_total(row, group):
                dropped.append((row, group))
    if len(dropped) < sample_size:
        raise RuntimeError(f"Need {sample_size} dropped issuer totals, found {len(dropped)}")
    selected = random.Random(seed + 1).sample(sorted(dropped, key=lambda item: item[0]["facility_row_id"]), sample_size)
    output = []
    for row, siblings in sorted(selected, key=lambda item: item[0]["facility_row_id"]):
        detail = [other for other in siblings if decimal_or_none(other.get("principal")) is not None]
        output.append({
            "review_row_id": "AGG_DROP_" + sha256_bytes(row["facility_row_id"].encode("utf-8"))[:16],
            "facility_row_id": row["facility_row_id"],
            "ticker": row["ticker"],
            "period_end": row["period_end"],
            "observation_date": row["observation_date"],
            "borrower_norm": row["borrower_norm"],
            "raw_identifier": row["investment_identifier"],
            "debt_equity": row["debt_equity"],
            "facility_type": row["facility_type"],
            "lien": row["lien"],
            "currency": row["currency"],
            "reference_rate": row["reference_rate"],
            "spread": row["spread"],
            "maturity": row["maturity"],
            "funded_status": row["funded_status"],
            "principal": row["principal"],
            "cost": row["cost"],
            "fair_value": row["fair_value"],
            "sibling_identifiers_json": canonical_json(sorted({other["investment_identifier"] for other in siblings})),
            "principal_detail_sibling_count": len(detail),
            "proposed_drop_reason": "no principal; unspecified debt row; same borrower/accession has principal-bearing detail",
            "manual_should_drop_as_issuer_total": "",
            "review_notes": "",
        })
    return output, len(dropped)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--v1", type=Path, default=DEFAULT_V1)
    parser.add_argument("--multilot-output", type=Path, default=DEFAULT_MULTILOT)
    parser.add_argument("--dropped-output", type=Path, default=DEFAULT_DROPPED)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_META)
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    raw_rows = read_csv(args.raw)
    raw_by_id = {row["facility_row_id"]: row for row in raw_rows}
    multilot, multilot_universe = sample_multilot(read_csv(args.v1), raw_by_id, args.sample_size, args.seed)
    dropped, dropped_universe = sample_dropped(raw_rows, args.sample_size, args.seed)
    write_csv(args.multilot_output, multilot, MULTILOT_FIELDS)
    write_csv(args.dropped_output, dropped, DROPPED_FIELDS)
    metadata = {
        "seed": args.seed,
        "audit_target": "economic_facility_v1 before key correction",
        "normalized_input_sha256": sha256_file(args.raw),
        "v1_aggregate_sha256": sha256_file(args.v1),
        "multilot_universe_count": multilot_universe,
        "multilot_sample_size": len(multilot),
        "multilot_sample_file_sha256": sha256_file(args.multilot_output),
        "sampled_v1_groups_split_by_proposed_v2": sum(row["auto_v1_merges_multiple_v2_groups"] == "True" for row in multilot),
        "issuer_total_drop_universe_count": dropped_universe,
        "issuer_total_sample_size": len(dropped),
        "issuer_total_sample_file_sha256": sha256_file(args.dropped_output),
        "manual_multilot_reviews_complete": 0,
        "manual_issuer_total_reviews_complete": 0,
        "conclusion": "review files locked; automated v2-key split diagnostic recorded; human review labels pending",
    }
    write_json(args.metadata, metadata)
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

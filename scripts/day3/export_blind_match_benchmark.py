#!/usr/bin/env python3
"""Export a locked blind matching sample with no model predictions or evidence."""

import argparse
import json
import random
import sys
from pathlib import Path

DAY2 = Path(__file__).resolve().parents[1] / "day2"
sys.path.insert(0, str(DAY2))

from common import SEED, canonical_json, read_csv, sha256_bytes, sha256_file, write_csv, write_json  # noqa: E402


DEFAULT_INPUT = Path("/private/tmp/finance-day3-sec-cache/facility_candidates.csv")
DEFAULT_OUTPUT = Path("data/day3/blind_match_sample.csv")
DEFAULT_METADATA = Path("data/day3/blind_match_sample_meta.json")

FIELDS = [
    "blind_pair_id", "period_end", "quarter", "left_ticker", "right_ticker",
    "left_adsh", "right_adsh", "left_identifier", "right_identifier",
    "left_borrower_norm", "right_borrower_norm", "left_debt_equity",
    "right_debt_equity", "left_facility_type", "right_facility_type",
    "left_lien", "right_lien", "left_currency", "right_currency",
    "left_reference_rate", "right_reference_rate", "left_spread", "right_spread",
    "left_maturity", "right_maturity", "left_funded_status", "right_funded_status",
    "left_acquisition_date", "right_acquisition_date", "manual_label", "label_notes",
]

FORBIDDEN_SOURCE_FIELDS = {
    "predicted_label", "match_confidence", "evidence", "hard_conflicts",
    "informative_matches", "borrower_exact", "debt_equity_match",
    "facility_type_match", "lien_match", "currency_match",
    "reference_rate_match", "spread_match_25bp", "maturity_match_45d",
    "funded_status_match",
}


def export(rows, sample_size=60, seed=SEED):
    if len(rows) < sample_size:
        raise RuntimeError(f"Need {sample_size} candidates, found {len(rows)}")
    ordered = sorted(rows, key=lambda row: row["pair_id"])
    rng = random.Random(seed)
    selected = rng.sample(ordered, sample_size)
    selected.sort(key=lambda row: row["pair_id"])
    output = []
    for row in selected:
        if FORBIDDEN_SOURCE_FIELDS - set(row):
            raise RuntimeError("Candidate source schema is missing expected fields")
        output.append({
            "blind_pair_id": row["pair_id"],
            "period_end": row["period_end"],
            "quarter": row["quarter"],
            "left_ticker": row["left_ticker"],
            "right_ticker": row["right_ticker"],
            "left_adsh": row["left_adsh"],
            "right_adsh": row["right_adsh"],
            "left_identifier": row["left_identifier"],
            "right_identifier": row["right_identifier"],
            "left_borrower_norm": row["left_borrower_norm"],
            "right_borrower_norm": row["right_borrower_norm"],
            "left_debt_equity": row["left_debt_equity"],
            "right_debt_equity": row["right_debt_equity"],
            "left_facility_type": row["left_facility_type"],
            "right_facility_type": row["right_facility_type"],
            "left_lien": row["left_lien"],
            "right_lien": row["right_lien"],
            "left_currency": row["left_currency"],
            "right_currency": row["right_currency"],
            "left_reference_rate": row["left_reference_rate"],
            "right_reference_rate": row["right_reference_rate"],
            "left_spread": row["left_spread"],
            "right_spread": row["right_spread"],
            "left_maturity": row["left_maturity"],
            "right_maturity": row["right_maturity"],
            "left_funded_status": row["left_funded_status"],
            "right_funded_status": row["right_funded_status"],
            "left_acquisition_date": row["left_acquisition_date"],
            "right_acquisition_date": row["right_acquisition_date"],
            "manual_label": "",
            "label_notes": "",
        })
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--sample-size", type=int, default=60)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    sample = export(read_csv(args.input), args.sample_size, args.seed)
    write_csv(args.output, sample, FIELDS)
    ids = [row["blind_pair_id"] for row in sample]
    metadata = {
        "seed": args.seed,
        "sample_size": len(sample),
        "source_candidate_sha256": sha256_file(args.input),
        "blind_ids_sha256": sha256_bytes(canonical_json(ids).encode("utf-8")),
        "blind_file_sha256": sha256_file(args.output),
        "forbidden_columns_absent": sorted(FORBIDDEN_SOURCE_FIELDS),
        "labels_entered": False,
        "sampling": "simple random sample from the full aggregated candidate-pair universe",
        "pair_ids": ids,
    }
    write_json(args.metadata, metadata)
    print(json.dumps({key: value for key, value in metadata.items() if key != "pair_ids"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

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
DEFAULT_OUTPUT = Path("data/day3/blind_facility_pairs.csv")
DEFAULT_METADATA = Path("data/day3/blind_facility_pairs_meta.json")

SEEN_DEVELOPMENT_BORROWERS = {
    "PetVet Care Centers": {"petvet care centers", "romulus intermediate dba petvet care centers a stock"},
    "MRI Software": {"mri software"},
    "Anaplan": {"anaplan"},
    "Viant Medical": {"viant medical"},
    "Hyland Software": {"hyland software"},
    "Fortis Solutions": {"fortis solutions"},
    "PPV Intermediate": {"ppv intermediate"},
    "Ping Identity": {"ping identity"},
    "Pye-Barker": {"pye barker fire and safety"},
    "Auctane": {"auctane"},
    "Medallia": {"medallia"},
}

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


def contains_seen_borrower(row):
    borrowers = {row.get("left_borrower_norm", "").lower(), row.get("right_borrower_norm", "").lower()}
    aliases = {alias for values in SEEN_DEVELOPMENT_BORROWERS.values() for alias in values}
    return bool(borrowers & aliases)


def seen_borrower_name(value):
    value = (value or "").lower()
    for canonical, aliases in SEEN_DEVELOPMENT_BORROWERS.items():
        if value in aliases:
            return canonical
    return ""


def export(rows, sample_size=60, seed=SEED):
    eligible = [row for row in rows if not contains_seen_borrower(row)]
    if len(eligible) < sample_size:
        raise RuntimeError(f"Need {sample_size} uncontaminated candidates, found {len(eligible)}")
    ordered = sorted(eligible, key=lambda row: row["pair_id"])
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
        "sampling": "simple random sample after pre-sampling exclusion of seen development borrowers",
        "correction_status": "resampled_before_any_manual_labels",
        "superseded_blind_ids_sha256": "b748cd5b992e4ffcb8e9d8c95d745ffbe2ab5f58330256452ca53b174bf03a1f",
        "correction_reason": "Auctane and Medallia added; all 11 seen borrowers excluded across every period",
        "development_borrowers_excluded_before_sampling": sorted(SEEN_DEVELOPMENT_BORROWERS),
        "development_borrower_aliases": {
            key: sorted(values) for key, values in sorted(SEEN_DEVELOPMENT_BORROWERS.items())
        },
        "exclusion_scope": "all candidate periods, not only the development quarter",
        "development_borrower_pair_count_excluded": sum(contains_seen_borrower(row) for row in read_csv(args.input)),
        "pair_ids": ids,
    }
    write_json(args.metadata, metadata)
    print(json.dumps({key: value for key, value in metadata.items() if key != "pair_ids"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Create a 60/30/30 blind facility benchmark and a private row-level key."""

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

DAY2 = Path(__file__).resolve().parents[1] / "day2"
DAY3 = Path(__file__).resolve().parent
sys.path.insert(0, str(DAY2))
sys.path.insert(0, str(DAY3))

from common import SEED, canonical_json, read_csv, sha256_bytes, sha256_file, stable_id, write_csv, write_json  # noqa: E402
from export_blind_match_benchmark import contains_seen_borrower  # noqa: E402


DEFAULT_INPUT = Path("/private/tmp/finance-day3-sec-cache/facility_candidates.csv")
DEFAULT_OUTPUT = Path("data/day3/blind_facility_pairs_v2.csv")
DEFAULT_META = Path("data/day3/blind_facility_pairs_v2_meta.json")
DEFAULT_PRIVATE_KEY = Path("private/day3/blind_facility_key.json")
CLASSIFIER_COMMIT_SHA = "1b51413aeb7748745294dac94343cae1ae864d94"
CLASSIFIER_PATH = Path("scripts/day3/build_facility_candidates.py")

BLIND_FIELDS = [
    "blind_pair_id", "period_end", "quarter", "left_ticker", "right_ticker",
    "left_identifier", "right_identifier", "left_borrower_norm", "right_borrower_norm",
    "left_debt_equity", "right_debt_equity", "left_facility_type", "right_facility_type",
    "left_lien", "right_lien", "left_currency", "right_currency",
    "left_reference_rate", "right_reference_rate", "left_spread", "right_spread",
    "left_maturity", "right_maturity", "left_funded_status", "right_funded_status",
    "left_acquisition_date", "right_acquisition_date", "manual_label", "label_notes",
]

STRATUM_SIZES = {
    "predicted_same_facility_high": 60,
    "hard_same_borrower_different_facility": 30,
    "uncertain_alias_distractor": 30,
}

SIDE_FIELDS = [
    "ticker", "identifier", "borrower_norm", "debt_equity", "facility_type",
    "lien", "currency", "reference_rate", "spread", "maturity",
    "funded_status", "acquisition_date",
]


def candidate_stratum(row):
    if row["predicted_label"] == "same_facility" and row["match_confidence"] == "high":
        return "predicted_same_facility_high"
    if (
        row["predicted_label"] == "same_borrower_different_facility"
        and row["match_confidence"] == "high"
        and row["borrower_exact"] == "True"
    ):
        return "hard_same_borrower_different_facility"
    if row["predicted_label"] in {"uncertain", "unrelated"}:
        return "uncertain_alias_distractor"
    return ""


def swap_sides(row):
    swapped = dict(row)
    for field in SIDE_FIELDS:
        swapped[f"left_{field}"], swapped[f"right_{field}"] = row[f"right_{field}"], row[f"left_{field}"]
    swapped["left_row_id"], swapped["right_row_id"] = row["right_row_id"], row["left_row_id"]
    swapped["left_adsh"], swapped["right_adsh"] = row["right_adsh"], row["left_adsh"]
    return swapped


def sample_candidates(rows, seed=SEED):
    eligible = [row for row in rows if not contains_seen_borrower(row)]
    pools = {stratum: [] for stratum in STRATUM_SIZES}
    for row in eligible:
        stratum = candidate_stratum(row)
        if stratum:
            pools[stratum].append(row)
    rng = random.Random(seed)
    selected = []
    for stratum, size in STRATUM_SIZES.items():
        pool = sorted(pools[stratum], key=lambda row: row["pair_id"])
        if len(pool) < size:
            raise RuntimeError(f"Need {size} rows for {stratum}, found {len(pool)}")
        for row in rng.sample(pool, size):
            selected.append((stratum, row))
    rng.shuffle(selected)
    return selected, {key: len(value) for key, value in pools.items()}


def build(rows, seed=SEED):
    selected, pool_sizes = sample_candidates(rows, seed)
    rng = random.Random(seed + 17)
    blind = []
    private = []
    for position, (stratum, source) in enumerate(selected):
        swapped = bool(rng.getrandbits(1))
        display = swap_sides(source) if swapped else source
        blind_id = "BF2_" + stable_id(seed, position, source["pair_id"], length=22)
        row = {
            "blind_pair_id": blind_id,
            "period_end": display["period_end"],
            "quarter": display["quarter"],
            "manual_label": "",
            "label_notes": "",
        }
        for side in ("left", "right"):
            for field in SIDE_FIELDS:
                row[f"{side}_{field}"] = display[f"{side}_{field}"]
        blind.append(row)
        private.append({
            "blind_pair_id": blind_id,
            "hidden_stratum": stratum,
            "model_decision": {
                "predicted_label": source["predicted_label"],
                "match_confidence": source["match_confidence"],
                "evidence": source["evidence"],
            },
            "source_candidate_ids": {
                "candidate_pair_id": source["pair_id"],
                "left_facility_id": source["left_row_id"],
                "right_facility_id": source["right_row_id"],
            },
            "display_sides_swapped": swapped,
        })
    return blind, private, pool_sizes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_META)
    parser.add_argument("--private-key", type=Path, default=DEFAULT_PRIVATE_KEY)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    blind, private_rows, pool_sizes = build(read_csv(args.input), args.seed)
    write_csv(args.output, blind, BLIND_FIELDS)
    args.private_key.parent.mkdir(parents=True, exist_ok=True)
    private_payload = {
        "seed": args.seed,
        "classifier_commit_sha": CLASSIFIER_COMMIT_SHA,
        "candidate_file_sha256": sha256_file(args.input),
        "rows": private_rows,
    }
    write_json(args.private_key, private_payload)
    counts = Counter(row["hidden_stratum"] for row in private_rows)
    metadata = {
        "design_status": "ready_for_blind_labeling",
        "seed": args.seed,
        "sample_size": len(blind),
        "aggregate_hidden_stratum_counts": dict(sorted(counts.items())),
        "expected_counts": STRATUM_SIZES,
        "eligible_pool_counts": pool_sizes,
        "hidden_strata_present_in_blind_file": False,
        "left_right_order_randomized": True,
        "labels_entered": False,
        "development_borrowers_excluded_all_periods": True,
        "classifier_commit_sha": CLASSIFIER_COMMIT_SHA,
        "classifier_file_sha256": sha256_file(CLASSIFIER_PATH),
        "candidate_file_sha256": sha256_file(args.input),
        "blind_file_sha256": sha256_file(args.output),
        "private_key_sha256": sha256_file(args.private_key),
        "private_key_tracked_by_git": False,
        "row_level_stratum_mapping_in_git": False,
    }
    write_json(args.metadata, metadata)
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

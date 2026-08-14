#!/usr/bin/env python3
"""Export blind facility benchmark v3 after official-field lineage repair."""

import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

DAY2 = Path(__file__).resolve().parents[1] / "day2"
DAY3 = Path(__file__).resolve().parent
sys.path.insert(0, str(DAY2))
sys.path.insert(0, str(DAY3))

from common import read_csv, sha256_file, stable_id, write_csv, write_json  # noqa: E402
from export_stratified_blind_facilities import (  # noqa: E402
    BLIND_FIELDS, CLASSIFIER_PATH, SIDE_FIELDS,
    STRATUM_SIZES, sample_candidates, swap_sides,
)


OLD_BLIND = Path("data/day3/blind_facility_pairs_v2.csv")
DEFAULT_INPUT = Path("/private/tmp/finance-day3-sec-cache/facility_candidates_lineage_v2.csv")
DEFAULT_OUTPUT = Path("data/day3/blind_facility_pairs_v3.csv")
DEFAULT_META = Path("data/day3/blind_facility_pairs_v3_meta.json")
DEFAULT_PRIVATE = Path("private/day3/blind_facility_v3_key.json")
CLASSIFIER_BASE_COMMIT_SHA = "05f982bd76da1499b10366bb52ae0281a138ec96"


def derive_seed(old_sha):
    material = "facility-blind-v3" + old_sha
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return digest, int(digest[:16], 16)


def build(rows, seed):
    selected, pool_sizes = sample_candidates(rows, seed)
    rng = random.Random(seed + 17)
    blind = []
    private = []
    for position, (stratum, source) in enumerate(selected):
        swapped = bool(rng.getrandbits(1))
        display = swap_sides(source) if swapped else source
        blind_id = "BF3_" + stable_id(seed, position, source["pair_id"], length=22)
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
    parser.add_argument("--private-key", type=Path, default=DEFAULT_PRIVATE)
    args = parser.parse_args()

    old_sha = sha256_file(OLD_BLIND)
    seed_digest, seed = derive_seed(old_sha)
    blind, private_rows, pool_sizes = build(read_csv(args.input), seed)
    write_csv(args.output, blind, BLIND_FIELDS)
    args.private_key.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.private_key, {
        "seed_derivation_sha256": seed_digest,
        "numeric_seed_first_64_bits": seed,
        "classifier_base_commit_sha": CLASSIFIER_BASE_COMMIT_SHA,
        "candidate_file_sha256": sha256_file(args.input),
        "rows": private_rows,
    })
    counts = Counter(row["hidden_stratum"] for row in private_rows)
    metadata = {
        "design_status": "ready_for_clean_blind_review_after_lineage_repair",
        "supersedes": str(OLD_BLIND),
        "supersession_reason": "parser_or_join_omission",
        "old_blind_file_sha256": old_sha,
        "seed_material": "sha256('facility-blind-v3' + old_blind_file_sha256)",
        "seed_derivation_sha256": seed_digest,
        "numeric_seed_first_64_bits": seed,
        "sample_size": len(blind),
        "aggregate_hidden_stratum_counts": dict(sorted(counts.items())),
        "expected_counts": STRATUM_SIZES,
        "eligible_pool_counts": pool_sizes,
        "hidden_strata_present_in_blind_file": False,
        "left_right_order_randomized": True,
        "labels_entered": False,
        "development_borrowers_excluded_all_periods": True,
        "classifier_base_commit_sha": CLASSIFIER_BASE_COMMIT_SHA,
        "classifier_file_sha256": sha256_file(CLASSIFIER_PATH),
        "candidate_file_sha256": sha256_file(args.input),
        "blind_file_sha256": sha256_file(args.output),
        "private_key_sha256": sha256_file(args.private_key),
        "private_key_tracked_by_git": False,
        "row_level_stratum_mapping_in_git": False,
    }
    write_json(args.metadata, metadata)
    write_json(Path("data/day3/blind_facility_pairs_v2_status.json"), {
        "status": "superseded_parser_or_join_omission",
        "file": str(OLD_BLIND),
        "file_sha256_unchanged": old_sha,
        "human_labels_opened_or_used": False,
        "private_v2_key_opened_or_used": False,
        "replacement": str(args.output),
    })
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Freeze candidate-pair IDs before any benchmark labels are entered."""

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from common import SEED, canonical_json, read_csv, sha256_bytes, sha256_file, write_csv, write_json


DEFAULT_INPUT = Path("data/day2/facility_candidates.csv")
DEFAULT_OUTPUT = Path("data/day2/locked_match_sample.csv")
DEFAULT_METADATA = Path("data/day2/locked_match_sample_meta.json")
LABEL_FIELDS = ["sample_seed", "sample_locked", "manual_label", "label_notes", "adjudicator"]


def locked_sample(rows, sample_size=240, seed=SEED):
    if len(rows) < 200:
        raise RuntimeError(f"At least 200 candidate pairs required, found {len(rows)}")
    rng = random.Random(seed)
    strata = defaultdict(list)
    for row in rows:
        strata[(row["predicted_label"], row["match_confidence"])].append(row)
    for values in strata.values():
        values.sort(key=lambda row: row["pair_id"])
        rng.shuffle(values)

    targets = {
        ("same_facility", "high"): 80,
        ("same_borrower_different_facility", "high"): 60,
        ("same_borrower_different_facility", "medium"): 30,
        ("uncertain", "low"): 50,
        ("unrelated", "high"): 20,
    }
    selected = []
    selected_ids = set()
    for key, target in targets.items():
        for row in strata.get(key, [])[:target]:
            selected.append(row)
            selected_ids.add(row["pair_id"])
    remaining = [row for row in rows if row["pair_id"] not in selected_ids]
    remaining.sort(key=lambda row: row["pair_id"])
    rng.shuffle(remaining)
    selected.extend(remaining[:max(0, min(sample_size, len(rows)) - len(selected))])
    if len(selected) < 200:
        raise RuntimeError(f"Locked sample unexpectedly smaller than 200: {len(selected)}")
    selected = sorted(selected[:sample_size], key=lambda row: row["pair_id"])
    return [
        {**row, "sample_seed": seed, "sample_locked": "True", "manual_label": "", "label_notes": "", "adjudicator": ""}
        for row in selected
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--sample-size", type=int, default=240)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    if args.output.exists():
        existing = read_csv(args.output)
        if any(row.get("manual_label") for row in existing):
            raise RuntimeError("Refusing to overwrite an adjudicated locked benchmark")
    rows = read_csv(args.input)
    sample = locked_sample(rows, args.sample_size, args.seed)
    fieldnames = list(sample[0])
    write_csv(args.output, sample, fieldnames)
    ids = [row["pair_id"] for row in sample]
    ids_payload = canonical_json({"seed": args.seed, "pair_ids": ids}).encode("utf-8")
    metadata = {
        "seed": args.seed,
        "sample_size": len(sample),
        "candidate_file_sha256": sha256_file(args.input),
        "locked_pair_ids_sha256": sha256_bytes(ids_payload),
        "labels_entered": False,
        "outcomes_viewed": False,
        "pair_ids": ids,
    }
    write_json(args.metadata, metadata)
    print(json.dumps({key: value for key, value in metadata.items() if key != "pair_ids"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

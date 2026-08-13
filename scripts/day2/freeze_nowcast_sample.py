#!/usr/bin/env python3
"""Freeze nowcast observation IDs before target values are revealed."""

import argparse
import json
import random
from pathlib import Path

from common import CONTAMINATED_CASE_IDS, SEED, canonical_json, read_csv, sha256_bytes, sha256_file, write_json


DEFAULT_INPUT = Path("data/day3/eligible_prefreeze_ids.csv")
DEFAULT_OUTPUT = Path("data/day3/frozen_nowcast_sample.json")
DEFAULT_EVALUATOR = Path("scripts/day2/evaluate_nowcasts.py")
DEFAULT_PREREGISTRATION = Path("docs/research/PREREGISTRATION_V3.md")


def freeze(rows, sample_size=15, seed=SEED):
    if len(rows) < 10:
        raise RuntimeError(f"Need at least 10 eligible observations, found {len(rows)}")
    ids = sorted(row["observation_id"] for row in rows)
    rng = random.Random(seed)
    selected = sorted(rng.sample(ids, min(sample_size, len(ids))))
    payload = {"seed": seed, "observation_ids": selected}
    return {
        **payload,
        "eligible_count": len(ids),
        "eligible_ids_sha256": sha256_bytes(canonical_json(ids).encode("utf-8")),
        "frozen_sample_sha256": sha256_bytes(canonical_json(payload).encode("utf-8")),
        "outcomes_revealed": False,
        "contaminated_case_ids_excluded": sorted(CONTAMINATED_CASE_IDS),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--sample-size", type=int, default=15)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--evaluator", type=Path, default=DEFAULT_EVALUATOR)
    parser.add_argument("--preregistration", type=Path, default=DEFAULT_PREREGISTRATION)
    args = parser.parse_args()
    if args.output.exists():
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        if existing.get("outcomes_revealed"):
            raise RuntimeError("Refusing to overwrite a sample after outcomes were revealed")
    if not args.preregistration.exists():
        raise RuntimeError(
            f"Preregistration v3 is required before a new freeze: {args.preregistration}"
        )
    frozen = freeze(read_csv(args.input), args.sample_size, args.seed)
    frozen["eligible_file_sha256"] = sha256_file(args.input)
    frozen["evaluation_script"] = str(args.evaluator)
    frozen["evaluation_script_sha256"] = sha256_file(args.evaluator)
    frozen["preregistration_file"] = str(args.preregistration)
    frozen["preregistration_sha256"] = sha256_file(args.preregistration)
    write_json(args.output, frozen)
    print(json.dumps(frozen, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Validate and freeze the outcome-blind Day 5 human event consensus.

This Phase A utility does not access the private layer key or any
target-current data.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path


EXPECTED_CONSENSUS_SHA256 = "aef9a7d0e5fc89ef9e6d019f0ea0f1f09495089fcad74590e4747b4e27c2902b"
EXPECTED_BLIND_SHA256 = "4f7c0e8941a321a7e95d5395ce60182f380a063933dc2f2c8dc5373771172625"
EXPECTED_PREREGISTRATION_DRAFT_SHA256 = "65bf2b2a88cc61521eaaf2dd0e43af8a992a6fb4d1c1cc0dd4d8ef3bb434fd44"
EXPECTED_EVALUATOR_SHA256 = "ecc92fb08bbf18781b88a24ba44a2d2c152eb9ac2d8d62d582606b5091f73ac4"
REVIEWER_X_SHA256 = "10c1205b431138c0c9c9e945e72cee7cdf3b0eba6301498af3010d765f02909e"
REVIEWER_Y_SHA256 = "eac24a94217df0afd314d4cb3adca02f3a394e666cc84d25de709d328406a877"
ADJUDICATOR_H_SHA256 = "bbe51c86848a7b8d873ae617474e602a86a0c3b4deeaacc438243ea8f52dedb2"

REVIEW_CHECKS = (
    "source_temporal_same_facility",
    "source_to_target_prior_same_facility",
    "source_aggregation_valid",
    "target_prior_aggregation_valid",
)
REVIEW_FIELDS = (*REVIEW_CHECKS, "include_for_replication", "review_notes")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ordered_sha256(values) -> str:
    payload = json.dumps(list(values), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def mechanical_inclusion(row: dict[str, str]) -> str:
    labels = [row[field] for field in REVIEW_CHECKS]
    if any(label not in {"yes", "no", "uncertain"} for label in labels):
        raise RuntimeError("Human consensus contains an invalid review label")
    if "no" in labels:
        return "no"
    if "uncertain" in labels:
        return "uncertain"
    return "yes"


def validate(blind_path: Path, supplied_path: Path) -> dict:
    if sha256_file(supplied_path) != EXPECTED_CONSENSUS_SHA256:
        raise RuntimeError("Supplied consensus SHA-256 mismatch")
    if sha256_file(blind_path) != EXPECTED_BLIND_SHA256:
        raise RuntimeError("Frozen blind packet SHA-256 mismatch")
    blind_header, blind_rows = read_csv(blind_path)
    consensus_header, consensus_rows = read_csv(supplied_path)
    if blind_header != consensus_header:
        raise RuntimeError("Human consensus changed the blind packet schema")
    if len(blind_rows) != 75 or len(consensus_rows) != 75:
        raise RuntimeError("Expected exactly 75 blind and consensus rows")

    blind_ids = [row["review_observation_id"] for row in blind_rows]
    consensus_ids = [row["review_observation_id"] for row in consensus_rows]
    if len(set(consensus_ids)) != 75 or consensus_ids != blind_ids:
        raise RuntimeError("Consensus IDs/order differ from the frozen blind packet")
    non_review_fields = [field for field in blind_header if field not in REVIEW_FIELDS]
    for index, (blind, consensus) in enumerate(zip(blind_rows, consensus_rows)):
        if any(blind[field] != consensus[field] for field in non_review_fields):
            raise RuntimeError(f"Non-review data changed at row {index + 1}")
        if mechanical_inclusion(consensus) != consensus["include_for_replication"]:
            raise RuntimeError(f"Mechanical inclusion mismatch at row {index + 1}")

    counts = Counter(row["include_for_replication"] for row in consensus_rows)
    if counts != Counter({"yes": 67, "uncertain": 7, "no": 1}):
        raise RuntimeError(f"Unexpected inclusion counts: {dict(counts)}")
    included = [row for row in consensus_rows if row["include_for_replication"] == "yes"]
    if len({row["source_event_cluster_id"] for row in included}) != 67:
        raise RuntimeError("Expected 67 included blind-union clusters")
    if len({row["normalized_borrower"] for row in included}) != 33:
        raise RuntimeError("Expected 33 included blind-union borrowers")
    return {
        "rows": consensus_rows,
        "ordered_ids": consensus_ids,
        "counts": dict(counts),
        "included_clusters": 67,
        "included_borrowers": 33,
    }


def write_freeze(
    validated: dict,
    output_consensus: Path,
    output_json: Path,
    output_doc: Path,
    blind_path: Path,
    preregistration_path: Path,
    evaluator_path: Path,
    supplied_path: Path,
) -> None:
    output_consensus.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(supplied_path, output_consensus)
    if sha256_file(output_consensus) != EXPECTED_CONSENSUS_SHA256:
        raise RuntimeError("Materialized consensus is not byte-identical")

    record = {
        "status": "phase_a_human_consensus_frozen_outcome_blind",
        "consensus_path": str(output_consensus),
        "consensus_sha256": EXPECTED_CONSENSUS_SHA256,
        "blind_packet_path": str(blind_path),
        "blind_packet_sha256": sha256_file(blind_path),
        "preregistration_draft_sha256": sha256_file(preregistration_path),
        "evaluator_sha256": sha256_file(evaluator_path),
        "reviewer_input_sha256": {
            "reviewer_x": REVIEWER_X_SHA256,
            "reviewer_y": REVIEWER_Y_SHA256,
            "adjudicator_h": ADJUDICATOR_H_SHA256,
        },
        "ordered_review_observation_ids": validated["ordered_ids"],
        "ordered_review_observation_ids_sha256": ordered_sha256(validated["ordered_ids"]),
        "counts": {
            "total": 75,
            "include_yes": validated["counts"]["yes"],
            "include_uncertain": validated["counts"]["uncertain"],
            "include_no": validated["counts"]["no"],
            "included_blind_union_source_event_clusters": validated["included_clusters"],
            "included_blind_union_borrowers": validated["included_borrowers"],
        },
        "checks": {
            "consensus_sha_verified": True,
            "exact_frozen_blind_ids_and_order": True,
            "all_non_review_fields_unchanged": True,
            "mechanical_inclusion_verified_all_rows": True,
            "private_layer_membership_key_opened": False,
            "target_current_data_opened": False,
            "human_labels_or_notes_changed": False,
        },
    }
    if record["preregistration_draft_sha256"] != EXPECTED_PREREGISTRATION_DRAFT_SHA256:
        raise RuntimeError("Preregistration draft SHA-256 mismatch")
    if record["evaluator_sha256"] != EXPECTED_EVALUATOR_SHA256:
        raise RuntimeError("Evaluator SHA-256 mismatch")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    output_doc.parent.mkdir(parents=True, exist_ok=True)
    output_doc.write_text(
        "# Day 5 Phase A event-review freeze\n\n"
        "Status: **frozen outcome-blind human consensus**\n\n"
        f"- Final consensus SHA-256: `{EXPECTED_CONSENSUS_SHA256}`\n"
        f"- Frozen blind packet SHA-256: `{EXPECTED_BLIND_SHA256}`\n"
        f"- Preregistration draft SHA-256: `{EXPECTED_PREREGISTRATION_DRAFT_SHA256}`\n"
        f"- Evaluator SHA-256: `{EXPECTED_EVALUATOR_SHA256}`\n"
        f"- Reviewer X input SHA-256: `{REVIEWER_X_SHA256}`\n"
        f"- Reviewer Y input SHA-256: `{REVIEWER_Y_SHA256}`\n"
        f"- Adjudicator H SHA-256: `{ADJUDICATOR_H_SHA256}`\n\n"
        "The final file contains exactly 75 unique review IDs in the original blind-packet order. "
        "All non-review fields are byte-for-byte equal after CSV parsing, every inclusion label "
        "satisfies the locked mechanical rule, and the counts are 67 `yes`, 7 `uncertain`, and "
        "1 `no`. The 67 included blind-union rows contain 67 source-event clusters and 33 "
        "normalized borrowers.\n\n"
        "At this commit boundary the private STRICT/SUPPORTING membership key had not been "
        "opened. Target-current structure, valuation values, predictions, errors, and model "
        "results also remained unopened. Human labels and notes were not changed.\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--supplied-consensus", type=Path, required=True)
    parser.add_argument("--blind", type=Path, default=Path("data/day5/day5_event_review_blind.csv"))
    parser.add_argument("--preregistration", type=Path, default=Path("docs/research/DAY5_REPLICATION_PREREGISTRATION_DRAFT.md"))
    parser.add_argument("--evaluator", type=Path, default=Path("scripts/day5/evaluate_day5_replication.py"))
    parser.add_argument("--output-consensus", type=Path, default=Path("data/day5/day5_event_review_human_consensus.csv"))
    parser.add_argument("--output-json", type=Path, default=Path("data/day5/day5_phase_a_event_review_freeze.json"))
    parser.add_argument("--output-doc", type=Path, default=Path("docs/research/DAY5_PHASE_A_EVENT_REVIEW_FREEZE.md"))
    args = parser.parse_args()
    validated = validate(args.blind, args.supplied_consensus)
    write_freeze(
        validated,
        args.output_consensus,
        args.output_json,
        args.output_doc,
        args.blind,
        args.preregistration,
        args.evaluator,
        args.supplied_consensus,
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Validate and freeze the outcome-blind Day 5 Phase C consensus."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path


CONSENSUS_SHA256 = "44cacbe1fd93b030a51e1e4a9bac270c746a0baef6558372fab384221a50365e"
AUDIT_SHA256 = "9419d0039a689d7ff8a4847f099ff72232bc1d69222c345d71751a003909c77f"
REVIEWER_HASHES = {
    "reviewer_i": "4052ac40e9143cf4049427baca5820dd447ba673008415d3d18b45d2fe84d505",
    "reviewer_j": "ede4f83d07d9a4706f7a8e17873777ba2afb7149bc3f65b1de7274ce819fa8d7",
    "adjudicator_k": "6bdb2fff24719d019b615d9946347dadd896f5342ecbf53228d480e68ed6a60e",
}
PHASE_B_COMMIT = "f7ee622aa256dd4ba136dc8de2b477076d8a0229"
HASHES = {
    "strict_sample": "a42c462a83d960ed241fc48d91b89035a7cd0be44aeca0dcac5d20453b5719dd",
    "supporting_sample": "d4890bcbce1f8880cb56ca9ffe86071d3514064d4ff8488c685ef5f3cb62b50f",
    "event_consensus": "aef9a7d0e5fc89ef9e6d019f0ea0f1f09495089fcad74590e4747b4e27c2902b",
    "preregistration": "909b4068e335cedbe1c819ed47c0e35ffbd6f0ebc9b8bd89ad8f99365a39f1fb",
    "evaluator": "ecc92fb08bbf18781b88a24ba44a2d2c152eb9ac2d8d62d582606b5091f73ac4",
    "day4_logic": "bcea297f43603316d4d3bc5fef9762bc2749eaddf36a3253222af66e8f132615",
}
LABEL_FIELDS = (
    "target_current_same_facility",
    "target_current_aggregation_valid",
    "position_status",
)
REVIEW_FIELDS = (*LABEL_FIELDS, "structural_notes")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def file_assert(path: Path, expected: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"SHA mismatch for {path}: {actual}")


def summary(rows: list[dict[str, str]]) -> dict:
    counts = Counter(row["position_status"] for row in rows)
    continuing = [row for row in rows if row["position_status"] == "continuing"]
    return {
        "observations": len(rows),
        "position_status_counts": dict(sorted(counts.items())),
        "continuing_observations": len(continuing),
        "continuing_source_event_clusters": len({row["source_event_cluster_id"] for row in continuing}),
        "continuing_unique_borrowers": len({row["normalized_borrower"] for row in continuing}),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--supplied-consensus", type=Path, required=True)
    parser.add_argument("--supplied-audit", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path("."))
    args = parser.parse_args()
    repo = args.repo.resolve()

    file_assert(args.supplied_consensus, CONSENSUS_SHA256)
    file_assert(args.supplied_audit, AUDIT_SHA256)
    for name, rel in {
        "strict_sample": "data/day5/day5_strict_included_sample.csv",
        "supporting_sample": "data/day5/day5_supporting_included_sample.csv",
        "event_consensus": "data/day5/day5_event_review_human_consensus.csv",
        "preregistration": "docs/research/DAY5_REPLICATION_PREREGISTRATION.md",
        "evaluator": "scripts/day5/evaluate_day5_replication.py",
        "day4_logic": "scripts/day4/evaluate_confirmatory_shadow_nav.py",
    }.items():
        file_assert(repo / rel, HASHES[name])

    blind_header, blind = read_csv(repo / "data/day5/day5_target_current_structural_review_blind.csv")
    consensus_header, consensus = read_csv(args.supplied_consensus)
    _, audit = read_csv(args.supplied_audit)
    _, strict = read_csv(repo / "data/day5/day5_strict_included_sample.csv")
    _, supporting = read_csv(repo / "data/day5/day5_supporting_included_sample.csv")
    ids = [row["review_observation_id"] for row in consensus]
    supporting_ids = [row["review_observation_id"] for row in supporting]
    strict_ids = [row["review_observation_id"] for row in strict]
    if len(ids) != 67 or len(set(ids)) != 67 or ids != supporting_ids:
        raise RuntimeError("Consensus IDs/order do not exactly equal frozen SUPPORTING sample")
    if ids != [row["review_observation_id"] for row in blind]:
        raise RuntimeError("Consensus IDs/order differ from blind structural packet")
    if [row["review_observation_id"] for row in audit] != ids:
        raise RuntimeError("Consensus audit IDs/order differ")
    nonreview = [field for field in blind_header if field not in REVIEW_FIELDS]
    for clean, final in zip(blind, consensus):
        if any(clean[field] != final[field] for field in nonreview):
            raise RuntimeError(f"Non-review field changed for {final['review_observation_id']}")
    origins = Counter(row["consensus_origin"] for row in audit)
    if origins != {"independent_reviewer_agreement": 64, "outcome_blind_adjudication": 3}:
        raise RuntimeError(f"Unexpected consensus origins: {origins}")
    for final, detail in zip(consensus, audit):
        if any(final[field] != detail[field] for field in consensus_header):
            raise RuntimeError(f"Audit/final consensus mismatch: {final['review_observation_id']}")
        if detail["consensus_origin"] == "independent_reviewer_agreement":
            for field in LABEL_FIELDS:
                if detail[f"reviewer_i_{field}"] != final[field] or detail[f"reviewer_j_{field}"] != final[field]:
                    raise RuntimeError(f"Agreement label mismatch: {final['review_observation_id']}")

    supporting_summary = summary(consensus)
    strict_set = set(strict_ids)
    strict_summary = summary([row for row in consensus if row["review_observation_id"] in strict_set])
    if supporting_summary != {
        "observations": 67,
        "position_status_counts": {"continuing": 47, "refinancing_amendment": 1, "uncertain": 2, "unmatched_disappearance": 17},
        "continuing_observations": 47,
        "continuing_source_event_clusters": 47,
        "continuing_unique_borrowers": 24,
    }:
        raise RuntimeError(f"Unexpected SUPPORTING summary: {supporting_summary}")
    if strict_summary != {
        "observations": 31,
        "position_status_counts": {"continuing": 14, "uncertain": 1, "unmatched_disappearance": 16},
        "continuing_observations": 14,
        "continuing_source_event_clusters": 14,
        "continuing_unique_borrowers": 10,
    }:
        raise RuntimeError(f"Unexpected STRICT summary: {strict_summary}")

    destination = repo / "data/day5/day5_structural_mapping_consensus.csv"
    shutil.copyfile(args.supplied_consensus, destination)
    audit_record = {
        "phase": "Day 5 Phase C outcome-blind structural consensus",
        "consensus_sha256": CONSENSUS_SHA256,
        "supplied_consensus_audit_sha256": AUDIT_SHA256,
        "reviewer_file_sha256": REVIEWER_HASHES,
        "consensus_origin_counts": dict(origins),
        "supporting": supporting_summary,
        "strict": strict_summary,
        "human_labels_modified": False,
        "numeric_outcomes_accessed": False,
    }
    write_json(repo / "data/day5/day5_structural_consensus_audit.json", audit_record)
    freeze = {
        **audit_record,
        "phase_b_sample_freeze_commit": PHASE_B_COMMIT,
        "frozen_file_sha256": HASHES,
        "supporting_frozen_observation_ids": supporting_ids,
        "strict_frozen_observation_ids": strict_ids,
        "strict_power_guard": {
            "required_continuing_clusters": 25,
            "required_continuing_borrowers": 15,
            "actual_continuing_clusters": 14,
            "actual_continuing_borrowers": 10,
            "bound_primary_status": "underpowered_inconclusive",
        },
        "numeric_reveal_authorized_in_this_record": False,
    }
    write_json(repo / "data/day5/day5_structural_mapping_freeze.json", freeze)
    doc = f"""# Day 5 Phase C structural consensus freeze

Status: **FROZEN — outcome-blind structural mapping; numeric reveal not part of this commit**

The final Reviewer I / Reviewer J consensus and the outcome-blind Adjudicator K decisions are frozen byte-for-byte. The consensus contains 67 unique SUPPORTING observations in the exact frozen order. The 31 STRICT IDs remain the unchanged Phase B subset. No row was added, replaced, or moved between layers, and no human label was modified.

## Integrity

- consensus SHA-256: `{CONSENSUS_SHA256}`
- supplied audit SHA-256: `{AUDIT_SHA256}`
- Phase B sample-freeze commit: `{PHASE_B_COMMIT}`
- independent agreement: 64 rows
- outcome-blind adjudication: 3 rows

## Frozen structural attrition

- SUPPORTING: 67 observations; 47 continuing clusters and 24 continuing borrowers; statuses `{json.dumps(supporting_summary['position_status_counts'], sort_keys=True)}`.
- STRICT: 31 observations; 14 continuing clusters and 10 continuing borrowers; statuses `{json.dumps(strict_summary['position_status_counts'], sort_keys=True)}`.
- The STRICT primary status is therefore already bounded to `underpowered_inconclusive` by the unchanged 25-cluster / 15-borrower guards. Supporting evidence cannot override it.

## Boundary

This freeze contains no principal, cost, fair value, FV/principal, mark, prediction, error, effect size, MAE, p-value, or bootstrap result. Numeric reveal may begin only after this freeze exists as its own Git commit and the later authorization binds that full commit SHA.
"""
    (repo / "docs/research/DAY5_PHASE_C_STRUCTURAL_FREEZE.md").write_text(doc, encoding="utf-8")


if __name__ == "__main__":
    main()

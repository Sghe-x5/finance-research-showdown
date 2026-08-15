#!/usr/bin/env python3
"""Materialize the authorized Day 5 marks after the Phase C freeze."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


STRUCTURAL_FREEZE_COMMIT = "a94cf7159bea7465990ff1c7b3d390e56aa74c68"
EXPECTED = {
    "event_consensus": "aef9a7d0e5fc89ef9e6d019f0ea0f1f09495089fcad74590e4747b4e27c2902b",
    "strict_sample": "a42c462a83d960ed241fc48d91b89035a7cd0be44aeca0dcac5d20453b5719dd",
    "supporting_sample": "d4890bcbce1f8880cb56ca9ffe86071d3514064d4ff8488c685ef5f3cb62b50f",
    "structural_consensus": "44cacbe1fd93b030a51e1e4a9bac270c746a0baef6558372fab384221a50365e",
    "preregistration": "909b4068e335cedbe1c819ed47c0e35ffbd6f0ebc9b8bd89ad8f99365a39f1fb",
    "evaluator": "ecc92fb08bbf18781b88a24ba44a2d2c152eb9ac2d8d62d582606b5091f73ac4",
    "day4_logic": "bcea297f43603316d4d3bc5fef9762bc2749eaddf36a3253222af66e8f132615",
    "event_key": "6c8e142d9ff70af3bcee32a40fbbbb68ee459276d2a2ec449219123d61201733",
    "structural_key": "07a5fef79defb159916ef3c52563e1ca3512c2f132e81dd42e3e28d626af57bb",
    "historical_facilities": "535ec3a3e8e0e986881dbaa417cba441dd913be6186224ce166da6caea523a71",
    "new_facilities": "4a02fc27bba48c48ded40e96d231b1487659b7733f60326796da2e7e67896925",
}
OUTPUT_FIELDS = (
    "review_observation_id", "source_event_cluster_id", "borrower_norm",
    "report_period_label", "source_ticker", "target_ticker",
    "reporting_window_days", "target_prior_mark", "source_prior_mark",
    "source_current_mark", "target_current_mark",
    "target_current_same_facility", "target_current_aggregation_valid",
    "position_status",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_sha(path: Path, expected: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"SHA mismatch for {path}: {actual} != {expected}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_marks(paths: list[Path], wanted: set[str]) -> dict[str, str]:
    marks: dict[str, str] = {}
    for path in paths:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            id_index = header.index("economic_facility_id")
            mark_index = header.index("mark_fv_to_principal")
            for values in reader:
                facility_id = values[id_index]
                if facility_id in wanted:
                    value = values[mark_index]
                    if facility_id in marks and marks[facility_id] != value:
                        raise RuntimeError(f"Conflicting mark for {facility_id}")
                    marks[facility_id] = value
    missing = wanted - set(marks)
    if missing:
        raise RuntimeError(f"Missing {len(missing)} frozen facility IDs")
    return marks


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--historical-facilities", type=Path, default=Path("/private/tmp/finance-day3-sec-cache/bdc_facilities_all_agg.csv"))
    parser.add_argument("--new-facilities", type=Path, default=Path("/private/tmp/finance-day5-sec-cache/bdc_facilities_2026_new_agg.csv"))
    parser.add_argument("--event-key", type=Path, default=Path("private/day5/day5_event_review_key.json"))
    parser.add_argument("--structural-key", type=Path, default=Path("private/day5/day5_structural_review_evidence_key.json"))
    parser.add_argument("--output", type=Path, default=Path("data/day5/day5_revealed_replication_outcomes.csv"))
    parser.add_argument("--authorization", type=Path, default=Path("data/day5/day5_reveal_authorization.json"))
    args = parser.parse_args()
    repo = args.repo.resolve()
    paths = {
        "event_consensus": repo / "data/day5/day5_event_review_human_consensus.csv",
        "strict_sample": repo / "data/day5/day5_strict_included_sample.csv",
        "supporting_sample": repo / "data/day5/day5_supporting_included_sample.csv",
        "structural_consensus": repo / "data/day5/day5_structural_mapping_consensus.csv",
        "preregistration": repo / "docs/research/DAY5_REPLICATION_PREREGISTRATION.md",
        "evaluator": repo / "scripts/day5/evaluate_day5_replication.py",
        "day4_logic": repo / "scripts/day4/evaluate_confirmatory_shadow_nav.py",
        "event_key": repo / args.event_key,
        "structural_key": repo / args.structural_key,
        "historical_facilities": args.historical_facilities,
        "new_facilities": args.new_facilities,
    }
    for name, path in paths.items():
        assert_sha(path, EXPECTED[name])

    supporting = read_csv(paths["supporting_sample"])
    consensus = read_csv(paths["structural_consensus"])
    packet = {row["review_observation_id"]: row for row in read_csv(repo / "data/day5/day5_event_review_blind.csv")}
    ids = [row["review_observation_id"] for row in supporting]
    if ids != [row["review_observation_id"] for row in consensus] or len(ids) != 67:
        raise RuntimeError("Structural consensus and frozen SUPPORTING IDs/order differ")
    event_key = json.loads(paths["event_key"].read_text(encoding="utf-8"))["review_rows"]
    structural_key = json.loads(paths["structural_key"].read_text(encoding="utf-8"))["review_observation_mapping"]
    if any(value not in event_key or value not in structural_key or value not in packet for value in ids):
        raise RuntimeError("A frozen ID is missing from a private mapping or blind packet")

    facility_ids: set[str] = set()
    for observation_id in ids:
        key = event_key[observation_id]
        facility_ids.update((key["source_facility_id"], key["source_prior_facility_id"], key["target_prior_facility_id"]))
    for row in consensus:
        if row["position_status"] == "continuing":
            selected = structural_key[row["review_observation_id"]]["selected_economic_facility_id"]
            if not selected or structural_key[row["review_observation_id"]]["target_current_evidence_id"] != row["target_current_evidence_id"]:
                raise RuntimeError("Continuing target-current mapping is absent or inconsistent")
            facility_ids.add(selected)
    marks = load_marks([paths["historical_facilities"], paths["new_facilities"]], facility_ids)

    output = []
    for frozen, structure in zip(supporting, consensus):
        observation_id = frozen["review_observation_id"]
        key = event_key[observation_id]
        current_mark = ""
        if structure["position_status"] == "continuing":
            current_mark = marks[structural_key[observation_id]["selected_economic_facility_id"]]
        output.append({
            "review_observation_id": observation_id,
            "source_event_cluster_id": frozen["source_event_cluster_id"],
            "borrower_norm": frozen["normalized_borrower"],
            "report_period_label": frozen["report_period_label"],
            "source_ticker": frozen["source_ticker"],
            "target_ticker": frozen["target_ticker"],
            "reporting_window_days": packet[observation_id]["reporting_window_days"],
            "target_prior_mark": marks[key["target_prior_facility_id"]],
            "source_prior_mark": marks[key["source_prior_facility_id"]],
            "source_current_mark": marks[key["source_facility_id"]],
            "target_current_mark": current_mark,
            "target_current_same_facility": structure["target_current_same_facility"],
            "target_current_aggregation_valid": structure["target_current_aggregation_valid"],
            "position_status": structure["position_status"],
        })
    write_csv(repo / args.output, output)
    outcomes_sha = sha256_file(repo / args.output)
    authorization = {
        "event_review_consensus_sha256": EXPECTED["event_consensus"],
        "strict_included_sample_sha256": EXPECTED["strict_sample"],
        "supporting_included_sample_sha256": EXPECTED["supporting_sample"],
        "sample_freeze_commit": "f7ee622aa256dd4ba136dc8de2b477076d8a0229",
        "structural_mapping_consensus_sha256": EXPECTED["structural_consensus"],
        "structural_mapping_freeze_commit": STRUCTURAL_FREEZE_COMMIT,
        "preregistration_sha256": EXPECTED["preregistration"],
        "evaluator_sha256": EXPECTED["evaluator"],
        "day4_statistical_logic_sha256": EXPECTED["day4_logic"],
        "revealed_outcomes_sha256": outcomes_sha,
        "reveal_authorized": True,
    }
    (repo / args.authorization).write_text(json.dumps(authorization, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    required = ("target_prior_mark", "source_prior_mark", "source_current_mark", "target_current_mark")
    continuing = [row for row in output if row["position_status"] == "continuing"]
    print(json.dumps({
        "rows": len(output),
        "continuing_rows": len(continuing),
        "continuing_rows_missing_required_marks": sum(any(not row[field] for field in required) for row in continuing),
        "outcomes_sha256": outcomes_sha,
        "authorization": str(repo / args.authorization),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

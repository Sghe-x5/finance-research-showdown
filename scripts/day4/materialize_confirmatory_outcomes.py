#!/usr/bin/env python3
"""Materialize the authorized Phase D marks for the frozen 37-row sample."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


INCLUDED_SAMPLE_SHA256 = "011da2ab9ccc39f5c2530295fee1b555377f4a2b36a302e45183873af603a670"
STRUCTURAL_CONSENSUS_SHA256 = "a64a484f32f79f0053e06f15f2c0557e4198535a163fd29cb2a35fc73d91b768"
ELIGIBLE_SHA256 = "81c2cde597fd1b64499787da2ffa719682a27bd88f27d097e5eb459f410ddc24"
FACILITIES_SHA256 = "60aee6b26872b65a0845a58db286e3409518498532d2eb69d0ffc7c1d356bbec"
PRIVATE_STRUCTURAL_KEY_SHA256 = "9c6879c9f42b2a831a8e7427b5cb10282f591d2580f41cab753250c1d620b4d4"
EXPECTED_ROWS = 37

OUTPUT_FIELDS = (
    "review_observation_id",
    "source_event_cluster_id",
    "borrower_norm",
    "report_period_label",
    "source_ticker",
    "target_ticker",
    "reporting_window_days",
    "target_prior_mark",
    "source_prior_mark",
    "source_current_mark",
    "target_current_mark",
    "target_current_same_facility",
    "target_current_aggregation_valid",
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
        raise RuntimeError(f"Input SHA-256 mismatch for {path}: {actual} != {expected}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def stable_review_id(observation_id: str) -> str:
    return "D4R_" + hashlib.sha256(observation_id.encode("utf-8")).hexdigest()[:24]


def load_selected_marks(path: Path, wanted: set[str]) -> dict[str, str]:
    marks = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        id_index = header.index("economic_facility_id")
        mark_index = header.index("mark_fv_to_principal")
        for values in reader:
            facility_id = values[id_index]
            if facility_id in wanted:
                if facility_id in marks:
                    raise RuntimeError(f"Duplicate economic facility ID: {facility_id}")
                marks[facility_id] = values[mark_index]
    missing = wanted - set(marks)
    if missing:
        raise RuntimeError(f"Missing {len(missing)} frozen facility IDs")
    return marks


def numbers_match(left: str, right: str) -> bool:
    if not left or not right:
        return left == right
    return abs(float(left) - float(right)) <= 1e-12


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--included-sample",
        type=Path,
        default=Path("data/day4/confirmatory_included_sample.csv"),
    )
    parser.add_argument(
        "--structural-consensus",
        type=Path,
        default=Path("data/day4/day4_structural_mapping_consensus.csv"),
    )
    parser.add_argument(
        "--eligible",
        type=Path,
        default=Path("data/day3/eligible_prefreeze_extended.csv"),
    )
    parser.add_argument(
        "--facilities",
        type=Path,
        default=Path(
            "/private/tmp/finance-day3-sec-cache/bdc_facilities_agg_lineage_v2.csv"
        ),
    )
    parser.add_argument(
        "--private-structural-key",
        type=Path,
        default=Path("private/day4/structural_review_evidence_key.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/day4/revealed_confirmatory_outcomes.csv"),
    )
    args = parser.parse_args()

    for path, expected in (
        (args.included_sample, INCLUDED_SAMPLE_SHA256),
        (args.structural_consensus, STRUCTURAL_CONSENSUS_SHA256),
        (args.eligible, ELIGIBLE_SHA256),
        (args.facilities, FACILITIES_SHA256),
        (args.private_structural_key, PRIVATE_STRUCTURAL_KEY_SHA256),
    ):
        assert_sha(path, expected)

    included = read_csv(args.included_sample)
    structural = read_csv(args.structural_consensus)
    eligible = {
        stable_review_id(row["observation_id"]): row
        for row in read_csv(args.eligible)
    }
    private_key = json.loads(args.private_structural_key.read_text(encoding="utf-8"))
    current_evidence = private_key["target_current_evidence_mapping"]
    frozen_ids = [row["review_observation_id"] for row in included]
    structural_ids = [row["review_observation_id"] for row in structural]
    if frozen_ids != structural_ids or len(frozen_ids) != EXPECTED_ROWS:
        raise RuntimeError("Frozen and structural consensus IDs/order differ")
    if any(observation_id not in eligible for observation_id in frozen_ids):
        raise RuntimeError("Frozen observation is missing from pre-reveal eligibility")

    facility_ids = set()
    for observation_id in frozen_ids:
        source = eligible[observation_id]
        facility_ids.update({
            source["source_facility_id"],
            source["source_prior_facility_id"],
            source["target_prior_facility_id"],
        })
    for row in structural:
        evidence_id = row["target_current_evidence_id"]
        if evidence_id:
            if evidence_id not in current_evidence:
                raise RuntimeError("Target-current evidence ID is missing from private key")
            facility_ids.add(current_evidence[evidence_id]["economic_facility_id"])
    marks = load_selected_marks(args.facilities, facility_ids)

    output = []
    for frozen, structure in zip(included, structural):
        observation_id = frozen["review_observation_id"]
        source = eligible[observation_id]
        if not numbers_match(
            source["source_current_mark"], marks[source["source_facility_id"]]
        ):
            raise RuntimeError("Source-current mark conflicts with frozen eligibility")
        if not numbers_match(
            source["source_prior_mark"], marks[source["source_prior_facility_id"]]
        ):
            raise RuntimeError("Source-prior mark conflicts with frozen eligibility")
        target_current_mark = ""
        if structure["position_status"] == "continuing":
            evidence_id = structure["target_current_evidence_id"]
            if evidence_id:
                facility_id = current_evidence[evidence_id]["economic_facility_id"]
                target_current_mark = marks[facility_id]
        output.append({
            "review_observation_id": observation_id,
            "source_event_cluster_id": frozen["source_event_cluster_id"],
            "borrower_norm": frozen["normalized_borrower"],
            "report_period_label": frozen["report_period_label"],
            "source_ticker": frozen["source_ticker"],
            "target_ticker": frozen["target_ticker"],
            "reporting_window_days": source["reporting_window_days"],
            "target_prior_mark": marks[source["target_prior_facility_id"]],
            "source_prior_mark": marks[source["source_prior_facility_id"]],
            "source_current_mark": marks[source["source_facility_id"]],
            "target_current_mark": target_current_mark,
            "target_current_same_facility": structure[
                "target_current_same_facility"
            ],
            "target_current_aggregation_valid": structure[
                "target_current_aggregation_valid"
            ],
            "position_status": structure["position_status"],
        })

    if [row["review_observation_id"] for row in output] != frozen_ids:
        raise RuntimeError("Revealed outcome IDs/order changed")
    continuing = [row for row in output if row["position_status"] == "continuing"]
    required_marks = (
        "target_prior_mark",
        "source_prior_mark",
        "source_current_mark",
        "target_current_mark",
    )
    missing_continuing = sum(
        any(not row[field] for field in required_marks) for row in continuing
    )
    write_csv(args.output, output)
    print(json.dumps({
        "output": str(args.output),
        "sha256": sha256_file(args.output),
        "rows": len(output),
        "continuing_rows": len(continuing),
        "noncontinuing_rows_retained": len(output) - len(continuing),
        "continuing_rows_missing_required_marks": missing_continuing,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

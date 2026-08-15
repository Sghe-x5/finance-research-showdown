#!/usr/bin/env python3
"""Frozen-form Day 5 two-layer ShadowNAV replication evaluator.

This file is prepared before any Day 5 target-current reveal. The CLI refuses
to open outcomes without complete two-stage freeze authorization. Statistical
calculations reuse the byte-frozen Day 4 implementation and are exercised here
only with synthetic unit tests.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DAY4_EVALUATOR_PATH = ROOT / "scripts/day4/evaluate_confirmatory_shadow_nav.py"
DAY4_EVALUATOR_SHA256 = "bcea297f43603316d4d3bc5fef9762bc2749eaddf36a3253222af66e8f132615"

REQUIRED_AUTHORIZATION_FIELDS = (
    "event_review_consensus_sha256",
    "strict_included_sample_sha256",
    "supporting_included_sample_sha256",
    "sample_freeze_commit",
    "structural_mapping_consensus_sha256",
    "structural_mapping_freeze_commit",
    "preregistration_sha256",
    "evaluator_sha256",
    "day4_statistical_logic_sha256",
    "revealed_outcomes_sha256",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_day4_logic():
    if sha256_file(DAY4_EVALUATOR_PATH) != DAY4_EVALUATOR_SHA256:
        raise PermissionError("Frozen Day 4 statistical logic SHA-256 mismatch")
    spec = importlib.util.spec_from_file_location("frozen_day4_shadow_nav", DAY4_EVALUATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load frozen Day 4 evaluator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


day4 = load_day4_logic()


def read_sample(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        ids = payload.get("included_review_observation_ids") or payload.get("review_observation_ids")
        rows = [{"review_observation_id": value} for value in ids or []]
    else:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        ids = [row.get("review_observation_id", "") for row in rows]
    if not ids or any(not value for value in ids) or len(ids) != len(set(ids)):
        raise PermissionError("Included-sample IDs are empty, blank, or duplicated")
    return ids, rows


def verify_layer_ids(strict_ids: list[str], supporting_ids: list[str]) -> None:
    if not set(strict_ids) <= set(supporting_ids):
        raise PermissionError("Frozen STRICT sample is not a subset of SUPPORTING")


def verify_file_hash(path: Path, expected: str, label: str) -> None:
    if sha256_file(path) != expected:
        raise PermissionError(f"{label} SHA-256 mismatch")


def supporting_overlap_metadata(rows: list[dict[str, str]]) -> dict:
    def truthy(value: str) -> bool:
        return str(value).strip().lower() == "true"

    return {
        "observations": len(rows),
        "day4_borrower_overlap_observations": sum(
            truthy(row.get("overlap_day4_borrower", "")) for row in rows
        ),
        "development_borrower_overlap_observations": sum(
            truthy(row.get("overlap_development_borrower", "")) for row in rows
        ),
        "metadata_is_structural_not_an_outcome_filter": True,
    }


def secondary_supporting_output(raw: dict) -> dict:
    """Strip independent-decision authority from a supporting calculation."""
    raw = dict(raw)
    diagnostic = raw.pop("status")
    return {
        "label": "secondary_supporting",
        "can_modify_primary_status": False,
        "data_quality_inconclusive": diagnostic == "data_quality_inconclusive",
        "underpowered_for_frozen_procedures": diagnostic == "underpowered_inconclusive",
        "six_criteria_all_true": bool(
            raw.get("primary", {}).get("criteria")
            and all(raw["primary"]["criteria"].values())
        ),
        **raw,
    }


def evaluate_two_layers(
    rows: list[dict[str, str]],
    strict_ids: list[str],
    supporting_ids: list[str],
    supporting_sample_rows: list[dict[str, str]] | None = None,
) -> dict:
    """Evaluate authorized rows; intended for synthetic tests before reveal."""
    verify_layer_ids(strict_ids, supporting_ids)
    row_ids = [row.get("review_observation_id", "") for row in rows]
    if (
        any(not value for value in row_ids)
        or len(row_ids) != len(set(row_ids))
        or set(row_ids) != set(supporting_ids)
    ):
        raise PermissionError("Numeric outcome IDs do not exactly match SUPPORTING frozen IDs")
    by_id = {row["review_observation_id"]: row for row in rows}
    primary_strict = day4.evaluate_revealed_rows([by_id[value] for value in strict_ids])
    supporting_raw = day4.evaluate_revealed_rows([by_id[value] for value in supporting_ids])
    return {
        "status": primary_strict["status"],
        "primary_status_determined_only_by_strict": True,
        "primary_strict": primary_strict,
        "secondary_supporting": secondary_supporting_output(supporting_raw),
        "supporting_overlap": supporting_overlap_metadata(supporting_sample_rows or []),
    }


def load_authorized_inputs(
    outcomes_path: Path,
    strict_sample_path: Path,
    supporting_sample_path: Path,
    event_review_consensus_path: Path,
    structural_consensus_path: Path,
    preregistration_path: Path,
    authorization_path: Path,
    evaluator_path: Path | None = None,
) -> tuple[list[dict[str, str]], list[str], list[str], list[dict[str, str]]]:
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    if authorization.get("reveal_authorized") is not True:
        raise PermissionError("Day 5 target-outcome reveal is not authorized")
    if any(not authorization.get(field) for field in REQUIRED_AUTHORIZATION_FIELDS):
        raise PermissionError("Day 5 reveal authorization record is incomplete")
    if authorization["day4_statistical_logic_sha256"] != DAY4_EVALUATOR_SHA256:
        raise PermissionError("Authorization does not bind the frozen Day 4 logic")

    day4.verify_commit_pair(
        authorization["sample_freeze_commit"],
        authorization["structural_mapping_freeze_commit"],
    )
    for path, field, label in (
        (event_review_consensus_path, "event_review_consensus_sha256", "Event-review consensus"),
        (strict_sample_path, "strict_included_sample_sha256", "STRICT included sample"),
        (supporting_sample_path, "supporting_included_sample_sha256", "SUPPORTING included sample"),
        (structural_consensus_path, "structural_mapping_consensus_sha256", "Structural consensus"),
        (preregistration_path, "preregistration_sha256", "Preregistration"),
        (evaluator_path or Path(__file__).resolve(), "evaluator_sha256", "Evaluator self-file"),
        (DAY4_EVALUATOR_PATH, "day4_statistical_logic_sha256", "Frozen Day 4 logic"),
        (outcomes_path, "revealed_outcomes_sha256", "Revealed outcomes"),
    ):
        verify_file_hash(path, authorization[field], label)

    strict_ids, _strict_rows = read_sample(strict_sample_path)
    supporting_ids, supporting_rows = read_sample(supporting_sample_path)
    verify_layer_ids(strict_ids, supporting_ids)
    structural = day4.read_structural_consensus(structural_consensus_path, supporting_ids)
    with outcomes_path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    outcome_ids = [row.get("review_observation_id", "") for row in rows]
    if (
        any(not value for value in outcome_ids)
        or len(outcome_ids) != len(set(outcome_ids))
        or set(outcome_ids) != set(supporting_ids)
    ):
        raise PermissionError("Revealed outcome IDs do not exactly match SUPPORTING frozen IDs")
    day4.verify_outcomes_match_structural_consensus(rows, structural)
    return rows, strict_ids, supporting_ids, supporting_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revealed-outcomes", type=Path, required=True)
    parser.add_argument("--strict-included-sample", type=Path, required=True)
    parser.add_argument("--supporting-included-sample", type=Path, required=True)
    parser.add_argument("--event-review-consensus", type=Path, required=True)
    parser.add_argument("--structural-consensus", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows, strict_ids, supporting_ids, supporting_sample_rows = load_authorized_inputs(
        args.revealed_outcomes,
        args.strict_included_sample,
        args.supporting_included_sample,
        args.event_review_consensus,
        args.structural_consensus,
        args.preregistration,
        args.authorization,
    )
    result = evaluate_two_layers(rows, strict_ids, supporting_ids, supporting_sample_rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

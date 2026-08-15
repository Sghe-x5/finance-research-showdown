import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

from scripts.day5 import build_day5_event_review_packet as builder
from scripts.day5 import evaluate_day5_replication as evaluator


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "data/day5/replication_universe_candidates_v2.csv"
PACKET = ROOT / "data/day5/day5_event_review_blind.csv"
META = ROOT / "data/day5/day5_event_review_blind_meta.json"
PRIVATE_KEY = ROOT / "private/day5/day5_event_review_key.json"

FOUR_CHECKS = (
    "source_temporal_same_facility",
    "source_to_target_prior_same_facility",
    "source_aggregation_valid",
    "target_prior_aggregation_valid",
)


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def read_meta():
    return json.loads(META.read_text(encoding="utf-8"))


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_strict_supporting_membership_is_deterministic_and_nested():
    rows = read_csv(CANDIDATES)
    strict = [row for row in rows if row["strict_new_borrower_universe"] == "True"]
    supporting = [row for row in rows if row["new_fund_universe"] == "True"]
    strict_ids = {row["candidate_observation_id"] for row in strict}
    supporting_ids = {row["candidate_observation_id"] for row in supporting}

    assert strict_ids <= supporting_ids
    assert (len(strict), len({r["source_event_cluster_id"] for r in strict}), len({r["normalized_borrower"] for r in strict})) == (34, 34, 19)
    assert (len(supporting), len({r["source_event_cluster_id"] for r in supporting}), len({r["normalized_borrower"] for r in supporting})) == (75, 75, 39)

    meta = read_meta()
    assert meta["strict_is_subset_of_supporting"] is True
    assert meta["sha256"]["strict_candidate_observation_id_set"] == builder.canonical_set_sha256(strict_ids)
    assert meta["sha256"]["supporting_candidate_observation_id_set"] == builder.canonical_set_sha256(supporting_ids)


def test_blind_packet_has_exact_rows_and_no_layer_or_outcome_fields():
    rows = read_csv(PACKET)
    fields = set(rows[0])
    assert len(rows) == 75
    assert len({row["review_observation_id"] for row in rows}) == 75
    assert len({row["source_event_cluster_id"] for row in rows}) == 75
    assert all(row["review_observation_id"].startswith("D5EV_") for row in rows)
    assert not any("layer" in field.lower() for field in fields)
    assert not ({"strict_new_borrower_universe", "new_fund_universe"} & fields)
    assert not any("target_current" in field.lower() for field in fields)
    forbidden = (
        "principal", "cost", "fair_value", "fv_to_principal", "mark_fv",
        "prediction", "error", "return", "url", "accession", "provenance", "archive",
    )
    assert not any(token in field.lower() for field in fields for token in forbidden)


def test_blind_packet_contains_no_navigable_filing_evidence():
    text = PACKET.read_text(encoding="utf-8")
    assert not re.search(r"https?://|www\.|sec\.gov|/Archives/", text, re.IGNORECASE)
    assert not re.search(r"\b\d{10}-\d{2}-\d{6}\b", text)


def test_all_human_review_fields_are_blank():
    for row in read_csv(PACKET):
        assert all(row[field] == "" for field in (*FOUR_CHECKS, "include_for_replication", "review_notes"))


@pytest.mark.parametrize(
    ("labels", "expected"),
    [
        (("yes", "yes", "yes", "yes"), "yes"),
        (("yes", "no", "yes", "uncertain"), "no"),
        (("yes", "uncertain", "yes", "yes"), "uncertain"),
    ],
)
def test_mechanical_inclusion_rule(labels, expected):
    assert builder.mechanical_inclusion(labels) == expected


def test_packet_and_preparation_hashes_match_meta():
    meta = read_meta()
    assert meta["sha256"]["blind_review_packet"] == sha256(PACKET)
    assert meta["sha256"]["preregistration_draft"] == sha256(
        ROOT / "docs/research/DAY5_REPLICATION_PREREGISTRATION_DRAFT.md"
    )
    assert meta["sha256"]["evaluator"] == sha256(
        ROOT / "scripts/day5/evaluate_day5_replication.py"
    )
    assert meta["sha256"]["private_review_and_evidence_key"] == sha256(PRIVATE_KEY)
    ids = [row["review_observation_id"] for row in read_csv(PACKET)]
    assert meta["sha256"]["ordered_review_observation_ids"] == builder.ordered_sha256(ids)


def test_private_key_is_gitignored_and_untracked():
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", str(PRIVATE_KEY.relative_to(ROOT))],
        cwd=ROOT,
        check=False,
    )
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(PRIVATE_KEY.relative_to(ROOT))],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    assert ignored.returncode == 0
    assert tracked.returncode != 0


def test_supporting_calculation_cannot_override_primary_status(monkeypatch):
    calls = []

    def synthetic_result(rows):
        calls.append(len(rows))
        if len(rows) == 1:
            return {"status": "underpowered_inconclusive", "primary": {"criteria": {}}}
        return {"status": "pass", "primary": {"criteria": {f"criterion_{i}": True for i in range(6)}}}

    monkeypatch.setattr(evaluator.day4, "evaluate_revealed_rows", synthetic_result)
    rows = [{"review_observation_id": "strict"}, {"review_observation_id": "support-only"}]
    result = evaluator.evaluate_two_layers(rows, ["strict"], ["strict", "support-only"])
    assert calls == [1, 2]
    assert result["status"] == "underpowered_inconclusive"
    assert result["primary_strict"]["status"] == "underpowered_inconclusive"
    assert result["secondary_supporting"]["label"] == "secondary_supporting"
    assert result["secondary_supporting"]["can_modify_primary_status"] is False
    assert "status" not in result["secondary_supporting"]


def test_strict_power_guards_remain_25_clusters_and_15_borrowers():
    too_few_clusters = [
        {"source_event_cluster_id": f"c{i}", "borrower_norm": f"b{i % 15}"}
        for i in range(24)
    ]
    too_few_borrowers = [
        {"source_event_cluster_id": f"c{i}", "borrower_norm": f"b{i % 14}"}
        for i in range(25)
    ]
    assert evaluator.day4.continuing_power_guard(too_few_clusters)["status"] == "underpowered_inconclusive"
    assert evaluator.day4.continuing_power_guard(too_few_borrowers)["status"] == "underpowered_inconclusive"


def test_evaluator_refuses_outcome_id_mismatch(monkeypatch):
    monkeypatch.setattr(evaluator.day4, "evaluate_revealed_rows", lambda rows: {"status": "pass"})
    with pytest.raises(PermissionError, match="do not exactly match"):
        evaluator.evaluate_two_layers(
            [{"review_observation_id": "one"}],
            ["one"],
            ["one", "missing"],
        )


@pytest.mark.parametrize(
    ("field", "changed"),
    [
        ("position_status", "sale_exit"),
        ("target_current_same_facility", "no"),
        ("target_current_aggregation_valid", "uncertain"),
    ],
)
def test_evaluator_refuses_structural_label_mismatch(field, changed):
    structural = {
        "id": {
            "position_status": "continuing",
            "target_current_same_facility": "yes",
            "target_current_aggregation_valid": "yes",
        }
    }
    outcome = {
        "review_observation_id": "id",
        "position_status": "continuing",
        "target_current_same_facility": "yes",
        "target_current_aggregation_valid": "yes",
    }
    outcome[field] = changed
    with pytest.raises(PermissionError, match="cannot redefine"):
        evaluator.day4.verify_outcomes_match_structural_consensus([outcome], structural)


def test_preparation_snapshot_remains_outcome_blind_after_later_phases():
    forbidden = (
        "day5_sample_freeze.json",
        "day5_structural_consensus.csv",
        "day5_revealed_outcomes.csv",
    )
    for name in forbidden:
        assert not (ROOT / "data/day5" / name).exists()
    meta = read_meta()
    assert meta["prohibitions"] == {
        "final_sample_frozen": False,
        "predictions_errors_or_statistics_calculated": False,
        "result_tag_created": False,
        "target_current_numeric_marks_opened": False,
        "target_current_structure_opened": False,
    }

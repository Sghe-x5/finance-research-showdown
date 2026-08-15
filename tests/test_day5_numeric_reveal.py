import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def rows(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_numeric_outcomes_match_frozen_supporting_ids_and_structure():
    outcomes = rows(ROOT / "data/day5/day5_revealed_replication_outcomes.csv")
    supporting = rows(ROOT / "data/day5/day5_supporting_included_sample.csv")
    structure = rows(ROOT / "data/day5/day5_structural_mapping_consensus.csv")
    assert len(outcomes) == 67
    assert [r["review_observation_id"] for r in outcomes] == [r["review_observation_id"] for r in supporting]
    for outcome, frozen in zip(outcomes, structure):
        for field in ("target_current_same_facility", "target_current_aggregation_valid", "position_status"):
            assert outcome[field] == frozen[field]


def test_authorization_binds_frozen_evaluator_and_outcomes():
    auth = json.loads((ROOT / "data/day5/day5_reveal_authorization.json").read_text())
    evaluator = ROOT / "scripts/day5/evaluate_day5_replication.py"
    outcomes = ROOT / "data/day5/day5_revealed_replication_outcomes.csv"
    assert hashlib.sha256(evaluator.read_bytes()).hexdigest() == "ecc92fb08bbf18781b88a24ba44a2d2c152eb9ac2d8d62d582606b5091f73ac4"
    assert hashlib.sha256(outcomes.read_bytes()).hexdigest() == auth["revealed_outcomes_sha256"]
    assert auth["reveal_authorized"] is True


def test_primary_status_is_strict_only_and_supporting_is_secondary():
    result = json.loads((ROOT / "data/day5/day5_replication_results.json").read_text())
    assert result["status"] == result["primary_strict"]["status"] == "data_quality_inconclusive"
    assert result["primary_status_determined_only_by_strict"] is True
    assert result["primary_strict"]["primary_test_run"] is False
    assert result["primary_strict"]["continuing_rows_missing_marks"] == 2
    assert result["secondary_supporting"]["label"] == "secondary_supporting"
    assert result["secondary_supporting"]["can_modify_primary_status"] is False
    assert result["secondary_supporting"]["primary_test_run"] is False

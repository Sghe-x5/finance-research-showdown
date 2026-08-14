import csv
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from build_confirmatory_review_packet import PROHIBITED_OUTPUT_FIELDS, REVIEW_FIELDS
from evaluate_confirmatory_shadow_nav import (
    aggregate_source_event_clusters,
    attrition_flow,
    borrower_cluster_bootstrap_interval,
    leave_one_borrower_out,
    load_authorized_reveal,
    paired_permutation_pvalue,
    prediction_b0,
    prediction_shadow_nav,
)


def rows(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_confirmatory_review_packet_is_locked_and_outcome_blind():
    review = rows("data/day4/confirmatory_event_review_blind.csv")
    meta = payload("data/day4/confirmatory_event_review_meta.json")
    assert len(review) == 40
    assert len({row["review_observation_id"] for row in review}) == 40
    assert len({row["source_event_cluster_id"] for row in review}) == 37
    assert meta["review_packet_rows"] == 40
    assert meta["independent_source_event_clusters"] == 37
    assert len(meta["review_observation_ids_sha256"]) == 64
    assert len(meta["source_event_cluster_ids_sha256"]) == 64
    assert digest("data/day4/confirmatory_event_review_blind.csv") == meta["review_packet_sha256"]
    assert {row["report_period_label"] for row in review} == {
        "2024Q1", "2024Q2", "2024Q3", "2024Q4", "2025Q1", "2025Q2"
    }
    assert all(row["manager_relationship"] == "cross_manager" for row in review)
    assert all(not row[field] for row in review for field in REVIEW_FIELDS)
    headers = set(review[0])
    assert not (headers & PROHIBITED_OUTPUT_FIELDS)
    assert not any("target_current" in field for field in headers)
    assert meta["target_current_fields_present"] is False
    assert meta["target_outcomes_opened"] is False
    assert meta["source_or_target_numeric_marks_in_packet"] is False
    assert meta["principal_cost_or_fair_value_in_packet"] is False
    assert meta["model_prediction_in_packet"] is False
    assert meta["freeze_authorized"] is False
    assert meta["reveal_authorized"] is False


def test_packet_uses_exact_names_cross_manager_and_no_aliases():
    meta = payload("data/day4/confirmatory_event_review_meta.json")
    selection = meta["selection"]
    assert selection["exact_normalized_borrower_only"] is True
    assert selection["borrower_aliases_used"] is False
    assert selection["same_manager_observations_used"] is False
    assert selection["all_observations_cross_manager"] is True
    assert selection["development_period_excluded"] == "2025Q3"
    assert selection["economic_facility_rule"] == "economic_facility_v2"
    assert selection["movement_threshold"] == 0.005
    assert meta["periods"] == {
        "2024Q1": {"independent_source_event_clusters": 10, "observations": 11},
        "2024Q2": {"independent_source_event_clusters": 13, "observations": 14},
        "2024Q3": {"independent_source_event_clusters": 8, "observations": 9},
        "2024Q4": {"independent_source_event_clusters": 1, "observations": 1},
        "2025Q1": {"independent_source_event_clusters": 2, "observations": 2},
        "2025Q2": {"independent_source_event_clusters": 3, "observations": 3},
    }


def test_b0_and_source_delta_transfer_formulas():
    assert prediction_b0(0.91) == 0.91
    assert prediction_shadow_nav(0.91, 0.84, 0.90) == pytest.approx(0.85)
    assert prediction_shadow_nav(0.91, 1.02, 0.99) == pytest.approx(0.94)


def test_source_event_cluster_aggregation_gives_one_shock_one_vote():
    errors = [
        {
            "source_event_cluster_id": "A",
            "borrower_norm": "borrower-a",
            "report_period_label": "2024Q1",
            "source_ticker": "SRC",
            "target_ticker": "T1",
            "absolute_error_b0": 0.5,
            "absolute_error_sn": 0.3,
            "paired_error_difference": -0.2,
        },
        {
            "source_event_cluster_id": "A",
            "borrower_norm": "borrower-a",
            "report_period_label": "2024Q1",
            "source_ticker": "SRC",
            "target_ticker": "T2",
            "absolute_error_b0": 0.7,
            "absolute_error_sn": 0.3,
            "paired_error_difference": -0.4,
        },
        {
            "source_event_cluster_id": "B",
            "borrower_norm": "borrower-b",
            "report_period_label": "2024Q2",
            "source_ticker": "SRC2",
            "target_ticker": "T3",
            "absolute_error_b0": 0.2,
            "absolute_error_sn": 0.3,
            "paired_error_difference": 0.1,
        },
    ]
    clusters = aggregate_source_event_clusters(errors)
    assert len(clusters) == 2
    first = next(row for row in clusters if row["source_event_cluster_id"] == "A")
    assert first["target_count"] == 2
    assert first["mean_absolute_error_b0"] == pytest.approx(0.6)
    assert first["mean_absolute_error_sn"] == pytest.approx(0.3)
    assert first["mean_paired_error_difference"] == pytest.approx(-0.3)


def test_disappearance_flow_is_retained_without_mark_imputation():
    sample = [
        {"position_status": "continuing"},
        {"position_status": "partial_repayment"},
        {"position_status": "full_repayment"},
        {"position_status": "sale_exit"},
        {"position_status": "refinancing_amendment"},
        {"position_status": "unmatched_disappearance"},
    ]
    flow = attrition_flow(sample)
    assert all(flow[status] == 1 for status in flow)


def test_permutation_bootstrap_and_leave_one_borrower_are_deterministic():
    differences = [-0.10] * 8
    p_value = paired_permutation_pvalue(differences, draws=10_000, seed=20260814)
    assert 0 < p_value < 0.05
    clusters = [
        {
            "borrower_norm": f"borrower-{index}",
            "mean_paired_error_difference": value,
        }
        for index, value in enumerate((-0.10, -0.20, -0.30, -0.40))
    ]
    low, high = borrower_cluster_bootstrap_interval(clusters, draws=2_000, seed=20260814)
    assert low < high < 0
    loo = leave_one_borrower_out(clusters)
    assert len(loo) == 4
    assert all(value < 0 for value in loo.values())


def test_target_outcome_file_is_not_opened_without_authorization(tmp_path):
    authorization = tmp_path / "authorization.json"
    authorization.write_text('{"reveal_authorized": false}\n', encoding="utf-8")
    nonexistent_outcomes = tmp_path / "must_not_be_opened.csv"
    with pytest.raises(PermissionError, match="not authorized"):
        load_authorized_reveal(nonexistent_outcomes, authorization)
    assert not nonexistent_outcomes.exists()


def test_day4_evaluator_hash_and_git_boundaries():
    meta = payload("data/day4/confirmatory_evaluator_meta.json")
    assert digest("scripts/day4/evaluate_confirmatory_shadow_nav.py") == meta["evaluator_sha256"]
    assert meta["status"] == "prepared_synthetic_tests_only"
    assert meta["target_outcomes_opened"] is False
    assert meta["freeze_authorized"] is False
    assert meta["reveal_authorized"] is False
    assert meta["results_tag_authorized"] is False
    assert not Path("data/day4/frozen_confirmatory_sample.json").exists()
    tags = subprocess.check_output(["git", "tag", "--list"], text=True).splitlines()
    assert not any("day4" in tag.lower() for tag in tags)

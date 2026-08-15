import csv
import json
from pathlib import Path

import pytest

from build_pre_phase_b_audit import (
    DISTRIBUTION_FIELDS,
    build_duplicate_vote_audit,
    validate_phase_c_packet_schema,
)
from evaluate_confirmatory_shadow_nav import (
    borrower_clustered_permutation_pvalue,
    borrower_clustered_sign_flip_draw,
    continuing_power_guard,
    evaluate_revealed_rows,
)


class StubBits:
    def __init__(self, bits):
        self.bits = iter(bits)
        self.calls = 0

    def getrandbits(self, _width):
        self.calls += 1
        return next(self.bits)


def permutation_cluster(cluster_id, borrower, difference):
    return {
        "source_event_cluster_id": cluster_id,
        "borrower_norm": borrower,
        "mean_paired_error_difference": difference,
    }


def test_one_borrower_with_several_clusters_receives_one_shared_sign():
    clusters = [
        permutation_cluster("A", "same-borrower", -0.3),
        permutation_cluster("B", "same-borrower", 0.1),
        permutation_cluster("C", "same-borrower", -0.2),
    ]
    rng = StubBits([0])
    draw = borrower_clustered_sign_flip_draw(clusters, rng)
    assert rng.calls == 1
    assert {row["borrower_sign"] for row in draw} == {-1}
    assert [row["signed_paired_error_difference"] for row in draw] == pytest.approx(
        [0.3, -0.1, 0.2]
    )


def test_two_borrowers_receive_independent_sign_draws():
    clusters = [
        permutation_cluster("A", "borrower-a", -0.3),
        permutation_cluster("B", "borrower-a", -0.1),
        permutation_cluster("C", "borrower-b", -0.2),
    ]
    rng = StubBits([1, 0])
    draw = borrower_clustered_sign_flip_draw(clusters, rng)
    signs = {row["borrower_norm"]: row["borrower_sign"] for row in draw}
    assert rng.calls == 2
    assert signs == {"borrower-a": 1, "borrower-b": -1}


def test_borrower_clustered_permutation_is_order_invariant_and_deterministic():
    clusters = [
        permutation_cluster("A", "borrower-a", -0.3),
        permutation_cluster("B", "borrower-a", 0.1),
        permutation_cluster("C", "borrower-b", -0.2),
        permutation_cluster("D", "borrower-c", 0.05),
    ]
    first = borrower_clustered_permutation_pvalue(clusters, draws=5_000, seed=20260814)
    second = borrower_clustered_permutation_pvalue(
        list(reversed(clusters)), draws=5_000, seed=20260814
    )
    third = borrower_clustered_permutation_pvalue(clusters, draws=5_000, seed=20260814)
    assert first == second == third


def test_repeated_borrower_events_cannot_be_flipped_independently():
    clusters = [
        permutation_cluster("A", "borrower-a", -0.3),
        permutation_cluster("B", "borrower-a", -0.1),
    ]
    rng = StubBits([1])
    draw = borrower_clustered_sign_flip_draw(clusters, rng)
    assert rng.calls == 1
    assert len({row["borrower_sign"] for row in draw}) == 1


def test_fewer_than_15_unique_borrowers_forces_underpowered_inconclusive():
    clusters = [
        {"borrower_norm": f"borrower-{index % 14}"}
        for index in range(25)
    ]
    guard = continuing_power_guard(clusters)
    assert guard["status"] == "underpowered_inconclusive"
    assert guard["independent_continuing_source_event_clusters"] == 25
    assert guard["unique_continuing_borrowers"] == 14
    assert guard["failure_reasons"] == [
        "fewer_than_15_unique_continuing_borrowers"
    ]


def test_fewer_than_25_continuing_clusters_forces_underpowered_inconclusive():
    clusters = [
        {"borrower_norm": f"borrower-{index}"}
        for index in range(24)
    ]
    guard = continuing_power_guard(clusters)
    assert guard["status"] == "underpowered_inconclusive"
    assert guard["independent_continuing_source_event_clusters"] == 24
    assert guard["unique_continuing_borrowers"] == 24
    assert guard["failure_reasons"] == [
        "fewer_than_25_continuing_source_event_clusters"
    ]


def synthetic_revealed_rows(cluster_count, borrower_count):
    return [
        {
            "review_observation_id": f"R{index}",
            "source_event_cluster_id": f"C{index}",
            "borrower_norm": f"borrower-{index % borrower_count}",
            "report_period_label": "2024Q1",
            "source_ticker": "SRC",
            "target_ticker": "TGT",
            "reporting_window_days": "3",
            "position_status": "continuing",
            "target_prior_mark": "1.0",
            "source_prior_mark": "1.0",
            "source_current_mark": "0.9",
            "target_current_mark": "0.9",
        }
        for index in range(cluster_count)
    ]


@pytest.mark.parametrize(
    ("cluster_count", "borrower_count", "reason"),
    [
        (25, 14, "fewer_than_15_unique_continuing_borrowers"),
        (24, 24, "fewer_than_25_continuing_source_event_clusters"),
    ],
)
def test_evaluator_status_is_underpowered_when_either_guard_fails(
    cluster_count, borrower_count, reason
):
    result = evaluate_revealed_rows(
        synthetic_revealed_rows(cluster_count, borrower_count)
    )
    assert result["status"] == "underpowered_inconclusive"
    assert reason in result["power_guard"]["failure_reasons"]


def test_duplicate_economic_vote_prevents_future_freeze():
    included = [
        {
            "review_observation_id": "R1",
            "source_event_cluster_id": "C1",
            "period_end": "2024-03-31",
            "normalized_borrower": "borrower",
            "source_ticker": "SRC",
            "target_ticker": "TGT",
        },
        {
            "review_observation_id": "R2",
            "source_event_cluster_id": "C2",
            "period_end": "2024-03-31",
            "normalized_borrower": "borrower",
            "source_ticker": "SRC",
            "target_ticker": "TGT",
        },
    ]
    economic = {
        observation_id: {
            "report_period": "2024-03-31",
            "normalized_borrower": "borrower",
            "source_ticker": "SRC",
            "target_ticker": "TGT",
            "source_prior_economic_facility_id": "SOURCE-FACILITY",
            "target_prior_economic_facility_id": "TARGET-FACILITY",
        }
        for observation_id in ("R1", "R2")
    }
    consensus = {
        observation_id: {"include_for_confirmatory_test": "yes"}
        for observation_id in ("R1", "R2")
    }
    audit = build_duplicate_vote_audit(
        included,
        included,
        economic,
        consensus,
        {"consensus_sha256": "a" * 64},
        {},
    )
    assert audit["status"] == "duplicate_independent_vote_blocker"
    assert audit["duplicate_identities_found"] == 1
    assert audit["different_cluster_duplicate_identities"] == 1
    assert audit["affected_observation_ids"] == ["R1", "R2"]
    assert audit["affected_cluster_ids"] == ["C1", "C2"]
    assert audit["automatic_merge_or_row_selection_performed"] is False


def test_phase_c_packet_schema_excludes_phase_a_review_and_numeric_fields():
    validate_phase_c_packet_schema([
        "review_observation_id",
        "normalized_borrower",
        "target_current_facility_type",
        "target_current_lien",
        "target_current_currency",
        "target_current_reference_rate",
        "target_current_spread",
        "target_current_maturity",
        "target_current_funded_status",
        "target_current_constituent_descriptions",
        "target_current_aggregation_lot_count",
        "target_current_same_facility",
        "target_current_aggregation_valid",
        "position_status",
        "structural_notes",
    ])
    with pytest.raises(ValueError, match="Phase A or numeric/outcome fields"):
        validate_phase_c_packet_schema([
            "review_observation_id",
            "source_temporal_same_facility",
        ])
    with pytest.raises(ValueError, match="Phase A or numeric/outcome fields"):
        validate_phase_c_packet_schema([
            "review_observation_id",
            "target_current_mark",
        ])


def test_current_consensus_distribution_and_duplicate_vote_outputs_are_locked():
    with Path("data/day4/confirmatory_borrower_cluster_distribution.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        distribution = list(csv.DictReader(handle))
    audit = json.loads(
        Path("data/day4/confirmatory_duplicate_vote_audit.json").read_text(
            encoding="utf-8"
        )
    )
    assert tuple(distribution[0]) == DISTRIBUTION_FIELDS
    assert len(distribution) == 20
    assert sum(int(row["included_observation_count"]) for row in distribution) == 37
    assert sum(
        int(row["included_source_event_cluster_count"]) for row in distribution
    ) == 34
    assert max(
        int(row["included_source_event_cluster_count"]) for row in distribution
    ) == 5
    assert audit["included_rows_checked"] == 37
    assert audit["included_source_event_clusters_checked"] == 34
    assert audit["duplicate_identities_found"] == 0
    assert audit["affected_observation_ids"] == []
    assert audit["affected_cluster_ids"] == []
    assert audit["status"] == "pass_no_duplicate_independent_vote"
    assert audit["dealer_tire_uncertain_rows_not_promoted"] == 2
    assert audit["phase_b_freeze_created"] is False
    assert audit["target_current_structure_or_numeric_outcomes_opened"] is False


def test_no_phase_b_freeze_or_target_current_output_was_created():
    assert not Path("data/day4/frozen_confirmatory_sample.json").exists()
    assert not Path("data/day4/confirmatory_structural_review.csv").exists()
    if Path("data/day4/revealed_confirmatory_outcomes.csv").exists():
        assert Path("data/day4/confirmatory_sample_freeze.json").exists()
        assert Path("data/day4/structural_mapping_freeze.json").exists()

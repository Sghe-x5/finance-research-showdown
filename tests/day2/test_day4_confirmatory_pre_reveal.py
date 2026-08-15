import csv
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from evaluate_confirmatory_shadow_nav import (
    aggregate_source_event_clusters,
    attrition_flow,
    borrower_clustered_permutation_pvalue,
    borrower_cluster_bootstrap_interval,
    evaluate_revealed_rows,
    leave_one_borrower_out,
    load_authorized_reveal,
    prediction_b0,
    prediction_shadow_nav,
)
from sanitize_confirmatory_review_packet import (
    ACCESSION_RE,
    FORBIDDEN_HEADER_TOKENS,
    REVIEW_FIELDS,
    URL_RE,
)


def rows(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_rows(path, records):
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=records[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def test_sanitized_review_packet_is_locked_outcome_blind_and_non_navigable():
    review = rows("data/day4/confirmatory_event_review_blind_v2.csv")
    meta = payload("data/day4/confirmatory_event_review_blind_v2_meta.json")
    assert len(review) == 40
    assert len({row["review_observation_id"] for row in review}) == 40
    assert len({row["source_event_cluster_id"] for row in review}) == 37
    assert meta["review_observations"] == 40
    assert meta["independent_source_event_clusters"] == 37
    assert digest("data/day4/confirmatory_event_review_blind_v2.csv") == meta["sanitized_packet_sha256"]
    assert {row["report_period_label"] for row in review} == {
        "2024Q1", "2024Q2", "2024Q3", "2024Q4", "2025Q1", "2025Q2"
    }
    assert all(row["manager_relationship"] == "cross_manager" for row in review)
    assert all(not row[field] for row in review for field in REVIEW_FIELDS)
    headers = set(review[0])
    assert not any(
        token in header.lower() for header in headers for token in FORBIDDEN_HEADER_TOKENS
    )
    assert not any("target_current" in field for field in headers)
    assert all(
        not URL_RE.search(value or "") and not ACCESSION_RE.search(value or "")
        for row in review
        for value in row.values()
    )
    assert meta["no_url_columns"] is True
    assert meta["no_accession_or_document_identifier_columns"] is True
    assert meta["no_raw_provenance"] is True
    assert meta["no_target_current_fields"] is True
    assert meta["target_outcomes_opened"] is False
    assert meta["no_source_or_target_numeric_marks"] is True
    assert meta["no_principal_cost_or_fair_value"] is True
    assert meta["freeze_authorized"] is False
    assert meta["reveal_authorized"] is False


def test_sanitization_preserves_row_order_ids_clusters_and_marks_v1_superseded():
    old = rows("data/day4/confirmatory_event_review_blind.csv")
    clean = rows("data/day4/confirmatory_event_review_blind_v2.csv")
    meta = payload("data/day4/confirmatory_event_review_blind_v2_meta.json")
    assert [row["review_observation_id"] for row in old] == [
        row["review_observation_id"] for row in clean
    ]
    assert [row["source_event_cluster_id"] for row in old] == [
        row["source_event_cluster_id"] for row in clean
    ]
    assert meta["old_observation_id_set_sha256"] == meta["new_observation_id_set_sha256"]
    assert meta["old_cluster_id_set_sha256"] == meta["new_cluster_id_set_sha256"]
    assert meta["old_ordered_observation_ids_sha256"] == meta[
        "new_ordered_observation_ids_sha256"
    ]
    old_meta = payload("data/day4/confirmatory_event_review_meta.json")
    assert old_meta["status"] == "superseded_indirect_outcome_linkage_risk"


def test_private_evidence_key_is_ignored_and_only_its_hash_is_public():
    private_path = Path("private/day4/review_evidence_key.json")
    meta = payload("data/day4/confirmatory_event_review_blind_v2_meta.json")
    assert private_path.exists()
    assert digest(private_path) == meta["private_evidence_key_sha256"]
    assert subprocess.run(
        ["git", "check-ignore", "-q", str(private_path)], check=False
    ).returncode == 0
    assert subprocess.check_output(
        ["git", "ls-files", "private/day4"], text=True
    ).strip() == ""


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
        {"position_status": "uncertain"},
    ]
    flow = attrition_flow(sample)
    assert all(flow[status] == 1 for status in flow)


def test_permutation_bootstrap_and_leave_one_borrower_are_deterministic():
    permutation_clusters = [
        {
            "source_event_cluster_id": f"cluster-{index}",
            "borrower_norm": f"borrower-{index}",
            "mean_paired_error_difference": -0.10,
        }
        for index in range(8)
    ]
    p_value = borrower_clustered_permutation_pvalue(
        permutation_clusters, draws=10_000, seed=20260814
    )
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


def test_target_outcome_file_is_not_opened_before_phase_d_authorization(tmp_path):
    authorization = tmp_path / "authorization.json"
    authorization.write_text('{"reveal_authorized": false}\n', encoding="utf-8")
    nonexistent_outcomes = tmp_path / "must_not_be_opened.csv"
    with pytest.raises(PermissionError, match="not authorized"):
        load_authorized_reveal(
            nonexistent_outcomes,
            tmp_path / "included.csv",
            tmp_path / "event.csv",
            tmp_path / "structural.csv",
            tmp_path / "prereg.md",
            authorization,
        )
    assert not nonexistent_outcomes.exists()


def phase_d_fixture(
    tmp_path,
    included_ids=("A", "B"),
    outcome_ids=("A", "B"),
    structural_ids=None,
    structural_overrides=None,
    outcome_overrides=None,
):
    included = tmp_path / "included.csv"
    outcomes = tmp_path / "outcomes.csv"
    event = tmp_path / "event_consensus.csv"
    structural = tmp_path / "structural_consensus.csv"
    prereg = tmp_path / "preregistration.md"
    authorization = tmp_path / "authorization.json"
    write_rows(included, [{"review_observation_id": value} for value in included_ids])
    structural_ids = structural_ids or included_ids
    structural_overrides = structural_overrides or {}
    outcome_overrides = outcome_overrides or {}
    structural_rows = []
    for value in structural_ids:
        row = {
            "review_observation_id": value,
            "target_current_same_facility": "yes",
            "target_current_aggregation_valid": "yes",
            "position_status": "continuing",
        }
        row.update(structural_overrides.get(value, {}))
        structural_rows.append(row)
    outcome_rows = []
    for value in outcome_ids:
        row = {
            "review_observation_id": value,
            "target_current_same_facility": "yes",
            "target_current_aggregation_valid": "yes",
            "position_status": "continuing",
            "target_current_mark": "0.9",
        }
        row.update(outcome_overrides.get(value, {}))
        outcome_rows.append(row)
    write_rows(outcomes, outcome_rows)
    event.write_text("synthetic event consensus\n", encoding="utf-8")
    write_rows(structural, structural_rows)
    prereg.write_text("synthetic frozen preregistration\n", encoding="utf-8")
    sample_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD~1"], text=True
    ).strip()
    structural_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    auth = {
        "event_review_consensus_sha256": digest(event),
        "included_sample_sha256": digest(included),
        "sample_freeze_commit": sample_commit,
        "structural_mapping_consensus_sha256": digest(structural),
        "structural_mapping_freeze_commit": structural_commit,
        "preregistration_sha256": digest(prereg),
        "evaluator_sha256": digest("scripts/day4/evaluate_confirmatory_shadow_nav.py"),
        "revealed_outcomes_sha256": digest(outcomes),
        "reveal_authorized": True,
    }
    authorization.write_text(json.dumps(auth) + "\n", encoding="utf-8")
    return outcomes, included, event, structural, prereg, authorization, auth


def test_phase_d_requires_structural_consensus_hash_before_outcome_access(tmp_path):
    paths = phase_d_fixture(tmp_path)
    outcomes, included, event, structural, prereg, authorization, auth = paths
    auth.pop("structural_mapping_consensus_sha256")
    authorization.write_text(json.dumps(auth) + "\n", encoding="utf-8")
    outcomes.unlink()
    with pytest.raises(PermissionError, match="incomplete"):
        load_authorized_reveal(
            outcomes, included, event, structural, prereg, authorization
        )


def test_evaluator_verifies_its_own_sha_before_outcome_access(tmp_path):
    paths = phase_d_fixture(tmp_path)
    outcomes, included, event, structural, prereg, authorization, auth = paths
    auth["evaluator_sha256"] = "0" * 64
    authorization.write_text(json.dumps(auth) + "\n", encoding="utf-8")
    outcomes.unlink()
    with pytest.raises(PermissionError, match="Evaluator self-file SHA-256 mismatch"):
        load_authorized_reveal(
            outcomes, included, event, structural, prereg, authorization
        )


def test_revealed_ids_must_exactly_match_frozen_included_sample(tmp_path):
    paths = phase_d_fixture(tmp_path, included_ids=("A", "B"), outcome_ids=("A", "C"))
    outcomes, included, event, structural, prereg, authorization, _ = paths
    with pytest.raises(PermissionError, match="exactly match"):
        load_authorized_reveal(
            outcomes, included, event, structural, prereg, authorization
        )


def test_complete_synthetic_phase_d_authorization_allows_exact_id_set(tmp_path):
    paths = phase_d_fixture(tmp_path)
    outcomes, included, event, structural, prereg, authorization, _ = paths
    revealed = load_authorized_reveal(
        outcomes, included, event, structural, prereg, authorization
    )
    assert {row["review_observation_id"] for row in revealed} == {"A", "B"}


@pytest.mark.parametrize(
    ("field", "changed_value"),
    [
        ("position_status", "partial_repayment"),
        ("target_current_same_facility", "no"),
        ("target_current_aggregation_valid", "uncertain"),
    ],
)
def test_numeric_outcomes_cannot_redefine_structural_consensus(
    tmp_path, field, changed_value
):
    paths = phase_d_fixture(
        tmp_path,
        outcome_overrides={"A": {field: changed_value}},
    )
    outcomes, included, event, structural, prereg, authorization, _ = paths
    with pytest.raises(PermissionError, match="cannot redefine"):
        load_authorized_reveal(
            outcomes, included, event, structural, prereg, authorization
        )


@pytest.mark.parametrize("structural_ids", [("A",), ("A", "B", "C")])
def test_structural_consensus_ids_must_exactly_match_frozen_sample(
    tmp_path, structural_ids
):
    paths = phase_d_fixture(tmp_path, structural_ids=structural_ids)
    outcomes, included, event, structural, prereg, authorization, _ = paths
    with pytest.raises(PermissionError, match="Structural consensus IDs"):
        load_authorized_reveal(
            outcomes, included, event, structural, prereg, authorization
        )


def test_missing_human_confirmed_continuing_mark_forces_data_quality_inconclusive():
    result = evaluate_revealed_rows([
        {
            "review_observation_id": "synthetic",
            "source_event_cluster_id": "cluster",
            "borrower_norm": "borrower",
            "report_period_label": "2024Q1",
            "source_ticker": "SRC",
            "target_ticker": "TGT",
            "reporting_window_days": "3",
            "position_status": "continuing",
            "target_prior_mark": "0.90",
            "source_prior_mark": "0.90",
            "source_current_mark": "0.80",
            "target_current_mark": "",
        }
    ])
    assert result["status"] == "data_quality_inconclusive"
    assert result["continuing_rows_missing_marks"] == 1
    assert result["marks_imputed_or_rows_replaced"] is False
    assert result["primary_test_run"] is False


def test_day4_evaluator_hash_and_git_boundaries():
    meta = payload("data/day4/confirmatory_evaluator_meta.json")
    assert digest("scripts/day4/evaluate_confirmatory_shadow_nav.py") == meta["evaluator_sha256"]
    assert meta["status"] == "phase_b_frozen_synthetic_tests_only"
    assert meta["target_outcomes_opened"] is False
    assert meta["freeze_authorized"] is True
    assert meta["reveal_authorized"] is False
    assert meta["results_tag_authorized"] is False
    assert Path("data/day4/confirmatory_sample_freeze.json").exists()
    tags = subprocess.check_output(["git", "tag", "--list"], text=True).splitlines()
    day4_tags = [tag for tag in tags if "day4" in tag.lower()]
    assert day4_tags == ["shadownav-day4-confirmatory-2026-08-15"]
    target = subprocess.check_output(
        ["git", "rev-parse", f"{day4_tags[0]}^{{}}"], text=True
    ).strip()
    assert target == "fc4a874f7ca26aff364557c73f2b6765a8b7b2f7"


def test_phase_b_freeze_materializes_exact_consensus_sample_and_hashes():
    consensus = rows("data/day4/day4_event_review_human_consensus.csv")
    included = rows("data/day4/confirmatory_included_sample.csv")
    distribution = rows("data/day4/confirmatory_borrower_cluster_distribution.csv")
    freeze = payload("data/day4/confirmatory_sample_freeze.json")
    assert digest("data/day4/day4_event_review_human_consensus.csv") == (
        "2a0c763e423b5616b3f9093f54a0073d5e8577b0fe4f5769fb2ca60ff26f9591"
    )
    assert len(consensus) == 40
    assert len(included) == 37
    assert len({row["source_event_cluster_id"] for row in included}) == 34
    assert len({row["normalized_borrower"] for row in included}) == 20
    assert {row["manager_relationship"] for row in included} == {"cross_manager"}
    assert "2025Q3" not in {row["report_period_label"] for row in included}
    assert digest("data/day4/confirmatory_included_sample.csv") == freeze[
        "included_sample_sha256"
    ]
    assert digest("data/day4/confirmatory_borrower_cluster_distribution.csv") == freeze[
        "borrower_cluster_distribution_sha256"
    ]
    cluster_counts = [
        int(row["included_source_event_cluster_count"]) for row in distribution
    ]
    assert {value: cluster_counts.count(value) for value in sorted(set(cluster_counts))} == {
        1: 13,
        2: 3,
        3: 2,
        4: 1,
        5: 1,
    }
    assert freeze["maximum_source_event_clusters_per_borrower"] == 5
    assert freeze["duplicate_vote_audit_status"] == "pass_no_duplicate_independent_vote"
    assert freeze["approval_record"]["decision"] == "APPROVE FOR PHASE B FREEZE"
    forbidden = ("target_current", "principal", "cost", "fair_value", "mark", "error")
    assert not any(token in str(freeze).lower() for token in forbidden)

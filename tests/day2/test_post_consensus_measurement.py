import hashlib
import json
import subprocess
from pathlib import Path

from evaluate_post_consensus_measurement import exact_one_sided_lower, wilson_interval


def payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_frozen_human_consensus_files_are_byte_identical():
    assert digest("data/day3/human_consensus_facility_labels_v3.csv") == (
        "09daa1904a2c90fcfbd533ea72130a3ec80a1f6ea032d539ef10e49950d30455"
    )
    assert digest("data/day3/human_consensus_alias_labels.csv") == (
        "d7a09d15bf832719b24c0a69b182cce2c5331acbf16b75a811106f173f127c2f"
    )
    manifest = payload("data/day3/HUMAN_CONSENSUS_MANIFEST.json")
    assert manifest["agreement"]["facility_rows"] == 120
    assert manifest["agreement"]["alias_rows"] == 128
    assert manifest["private_mapping_opened"] is False
    assert manifest["target_outcomes_revealed"] is False


def test_facility_primary_measurement_and_intervals():
    result = payload("data/day3/facility_blind_evaluation.json")
    primary = result["primary_measurement"]
    assert primary["sample_rows"] == 60
    assert primary["true_positive"] == 58
    assert primary["definite_false_positive"] == 2
    assert primary["unresolved"] == 0
    assert primary["conditional_precision_resolved"] == 58 / 60
    assert primary["strict_confirmation_rate"] == 58 / 60
    assert primary["definite_resolution_coverage"] == 1.0
    assert primary["uncertain_rate"] == 0.0
    low, high = wilson_interval(58, 60)
    assert primary["conditional_precision_wilson_two_sided_95"] == {
        "lower": low,
        "upper": high,
    }
    assert primary["conditional_precision_exact_one_sided_95_lower"] == exact_one_sided_lower(58, 60)
    assert result["measurement_status"] == "MEASUREMENT_INCONCLUSIVE_REQUIRES_HUMAN_INTERPRETATION"
    assert result["scope_statement"] == (
        "Recall is conditional on the generated candidate universe and is not population recall."
    )


def test_facility_manager_split_and_confusion_totals():
    result = payload("data/day3/facility_blind_evaluation.json")
    same = result["same_manager_vs_cross_manager"]["same_manager"]
    cross = result["same_manager_vs_cross_manager"]["cross_manager"]
    assert (same["sample_rows"], same["true_positive"], same["definite_false_positive"]) == (49, 47, 2)
    assert (cross["sample_rows"], cross["true_positive"], cross["definite_false_positive"]) == (11, 11, 0)
    assert sum(row["count"] for row in result["all_sample_manager_relationship_confusion"]) == 120
    false_positive = Path("data/day3/facility_false_positive_audit.csv").read_text(encoding="utf-8")
    assert "other_or_insufficient_official_fields,2,1.0" in false_positive


def test_alias_nonblank_and_group_metrics_exclude_blank_nonobservations():
    result = payload("data/day3/alias_blind_evaluation.json")
    rows = result["row_level_borrower_alias_measurement"]
    assert rows == {
        "confirmed_same_borrower": 18,
        "definite_nonmatch": 71,
        "nonblank_candidate_rows": 91,
        "resolution_coverage": 89 / 91,
        "resolved_candidate_precision": 18 / 89,
        "uncertain_rate": 2 / 91,
        "unresolved": 2,
    }
    blank = result["blank_candidate_policy"]
    assert blank["blank_candidate_rows"] == 37
    assert blank["classification"] == "non_observation"
    assert blank["included_in_metric_denominators"] is False
    assert blank["counted_as_true_negatives"] is False
    groups = result["group_level_30_borrowers"]
    assert groups["sampled_source_borrowers"] == 30
    assert groups["status_counts"] == {
        "at_least_one_confirmed_alias": 1,
        "no_candidate_observed": 20,
        "only_definite_nonmatches": 8,
        "unresolved_candidate_set": 1,
    }
    assert groups["groups_with_confirmed_alias_outside_exact_block"] == 1
    assert groups["lower_bound_alias_loss_rate_over_all_sampled_groups"] == 1 / 30
    assert result["facility_identity_within_confirmed_borrower_aliases"] == {
        "confirmed_alias_rows": 18,
        "same_facility_no": 16,
        "same_facility_uncertain": 2,
        "same_facility_yes": 0,
    }


def test_private_row_mappings_are_not_published_or_tracked():
    tracked = subprocess.check_output(["git", "ls-files", "private/day3"], text=True).strip()
    assert tracked == ""
    aggregate_outputs = [
        "data/day3/facility_blind_evaluation.json",
        "data/day3/facility_hidden_stratum_confusion.csv",
        "data/day3/facility_false_positive_audit.csv",
        "data/day3/alias_blind_evaluation.json",
        "data/day3/alias_group_level_results.csv",
        "data/day3/alias_nonblank_confusion.csv",
        "docs/research/BLIND_BENCHMARK_RESULTS.md",
    ]
    combined = "\n".join(Path(path).read_text(encoding="utf-8") for path in aggregate_outputs)
    assert "BF3_" not in combined
    assert "BA2_" not in combined
    assert "source_candidate_ids" not in combined
    assert "candidate_facility_id" not in combined


def test_no_target_reveal_or_universe_expansion_in_evaluator():
    facility = payload("data/day3/facility_blind_evaluation.json")
    alias = payload("data/day3/alias_blind_evaluation.json")
    assert facility["research_boundaries"] == {
        "human_consensus_labels_modified": False,
        "results_tag_created": False,
        "target_error_metrics_calculated": False,
        "target_outcomes_read": False,
        "target_same_quarter_marks_read": False,
        "universe_expanded": False,
    }
    assert alias["research_boundaries"]["target_outcomes_read"] is False
    source = Path("scripts/day3/evaluate_post_consensus_measurement.py").read_text(encoding="utf-8")
    for forbidden_input in (
        "eligible_prefreeze_extended.csv",
        "nowcast_results.csv",
        "bdc_facilities_agg.csv",
        "frozen_nowcast",
    ):
        assert forbidden_input not in source
    tags = subprocess.check_output(["git", "tag", "--list"], text=True).splitlines()
    assert not any("day3" in tag.lower() for tag in tags)

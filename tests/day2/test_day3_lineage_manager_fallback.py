import csv
import hashlib
import json
import subprocess
from pathlib import Path

from aggregate_facilities import maturity_month
from export_blind_match_benchmark import SEEN_DEVELOPMENT_BORROWERS


def rows(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_raw_to_normalized_field_lineage_and_repair_counts():
    audit = payload("data/day3/field_lineage_audit_summary.json")
    repair = payload("data/day3/bdc_normalized_lineage_v2_metadata.json")
    assert audit["audit_scope"]["archive_count"] == 8
    assert audit["audit_scope"]["identifier_text_used_to_infer_fields"] is False
    assert audit["pipeline_loss_found"] is True
    assert audit["fields"]["maturity"]["diagnosis"] == "join_loss"
    assert audit["fields"]["acquisition_date"]["diagnosis"] == "join_loss"
    assert audit["fields"]["reference_rate"]["diagnosis"] == "parser_loss"
    assert audit["fields"]["currency"]["diagnosis"] == "source_absent"
    assert repair["filled_missing"] == {
        "acquisition_date": 3349,
        "maturity": 2320,
        "reference_rate": 9,
    }
    assert repair["identifier_text_used_to_infer_fields"] is False
    assert repair["ambiguous_field_keys_not_applied"] == 0


def test_no_silent_field_loss_after_normalization():
    audit = payload("data/day3/field_lineage_audit_summary.json")
    assert all(field["aggregation_loss"] == 0 for field in audit["fields"].values())
    assert all(field["export_loss"] == 0 for field in audit["fields"].values())
    repair = payload("data/day3/bdc_normalized_lineage_v2_metadata.json")
    aggregate = payload("data/day3/bdc_facilities_agg_lineage_v2_metadata.json")
    candidates = payload("data/day3/facility_candidates_lineage_v2_metadata.json")
    assert aggregate["input_sha256"] == repair["output_sha256"]
    assert candidates["input_file_sha256"] == aggregate["output_sha256"]
    assert maturity_month("2031-07") == "2031-07"


def test_manager_map_is_complete_and_required_groups_match():
    manager_rows = rows("data/day3/bdc_manager_map.csv")
    assert len(manager_rows) == 19
    assert len({row["ticker"] for row in manager_rows}) == 19
    assert all(row["evidence_source"].startswith("https://www.sec.gov/Archives/") for row in manager_rows)
    assert all(row["confidence"] == "high" for row in manager_rows)
    manager = {row["ticker"]: row["canonical_manager"] for row in manager_rows}
    assert manager["ARCC"] == manager["ASIF"] == "Ares Management"
    assert manager["OBDC"] == manager["OCIC"] == "Blue Owl Credit"
    assert manager["BCRED"] == manager["BXSL"] == "Blackstone Credit & Insurance"


def test_manager_overlap_and_cross_manager_guard_use_no_target_outcome():
    summary = payload("data/day3/manager_overlap_audit_summary.json")
    assert summary["layers"]["facility_candidate_universe"]["same_manager_count"] == 18252
    assert summary["layers"]["facility_candidate_universe"]["cross_manager_count"] == 22088
    assert summary["layers"]["blind_facility_sample_v3"]["same_manager_count"] == 84
    assert summary["layers"]["blind_facility_sample_v3"]["cross_manager_count"] == 36
    assert summary["layers"]["eligible_pre_reveal"]["same_manager_count"] == 0
    assert summary["layers"]["eligible_pre_reveal"]["cross_manager_count"] == 131
    assert summary["cross_manager_untouched_movement_facilities"] == 37
    assert summary["cross_manager_primary_preregistration_stratum_allowed"] is True
    assert summary["target_current_outcomes_read"] is False
    assert summary["hidden_matcher_strata_read"] is False
    assert summary["human_labels_read"] is False


def test_blind_v2_and_alias_are_unchanged_and_v3_is_clean():
    expected = {
        "data/day3/blind_facility_pairs_v2.csv": "98876afb05fc9d9f1ff0fefad93f461762d4e297f3454d9c64fc8e242ad47d4f",
        "data/day3/blind_alias_candidates.csv": "d37f5daeb4eb6cee9e4ddb2e7690978a6ac899c30305b4fda268bb7424a8b64e",
    }
    for path, digest in expected.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
    status = payload("data/day3/blind_facility_pairs_v2_status.json")
    assert status["status"] == "superseded_parser_or_join_omission"
    assert status["file_sha256_unchanged"] == expected["data/day3/blind_facility_pairs_v2.csv"]

    v3 = rows("data/day3/blind_facility_pairs_v3.csv")
    meta = payload("data/day3/blind_facility_pairs_v3_meta.json")
    assert len(v3) == 120
    assert meta["aggregate_hidden_stratum_counts"] == {
        "hard_same_borrower_different_facility": 30,
        "predicted_same_facility_high": 60,
        "uncertain_alias_distractor": 30,
    }
    assert meta["blind_file_sha256"] == "f4ec256bf4502f5cb6979ff218d3b5457481f0ae21bdb75841d4bb3c1d357c2b"
    headers = {name.lower() for name in v3[0]}
    assert not any(token in header for header in headers for token in ("hidden", "predicted", "confidence", "stratum", "evidence"))
    assert all(not row["manual_label"] and not row["label_notes"] for row in v3)
    excluded = {alias for aliases in SEEN_DEVELOPMENT_BORROWERS.values() for alias in aliases}
    assert not ({row[side] for row in v3 for side in ("left_borrower_norm", "right_borrower_norm")} & excluded)


def test_private_keys_are_untracked_and_human_labels_absent():
    tracked_private = subprocess.check_output(["git", "ls-files", "private/day3"], text=True).strip()
    assert tracked_private == ""
    for path, fields in (
        ("data/day3/blind_facility_pairs_v2.csv", ("manual_label", "label_notes")),
        ("data/day3/blind_facility_pairs_v3.csv", ("manual_label", "label_notes")),
        ("data/day3/blind_alias_candidates.csv", ("manual_same_borrower", "manual_same_facility", "review_notes")),
    ):
        assert all(not row[field] for row in rows(path) for field in fields)


def test_all_periodic_fallbacks_are_audited_with_separate_clocks():
    audit_rows = rows("data/day3/fallback_audit.csv")
    summary = payload("data/day3/fallback_audit_summary.json")
    assert len(audit_rows) == 100
    assert all(row["audit_status"] == "complete" for row in audit_rows)
    assert summary["fallback_rows_audited"] == 100
    assert summary["target_cutoff_shifted"] == 0
    assert summary["source_mark_timestamp_shifted"] == 0
    assert summary["timestamps_differ"] == 0
    assert summary["movement_unique_facilities_before"] == 37
    assert summary["movement_unique_facilities_after"] == 37
    assert summary["movement_guard_remains_met"] is True
    assert summary["target_current_outcome_used"] is False


def test_no_day3_freeze_reveal_or_tag_was_created():
    tags = set(subprocess.check_output(["git", "tag", "--list"], text=True).splitlines())
    assert not any("day3" in tag.lower() for tag in tags)
    assert not Path("data/day3/frozen_nowcast_sample_v3.json").exists()
    readiness = Path("docs/research/BLIND_BENCHMARK_READINESS.md").read_text(encoding="utf-8")
    assert "CURRENT_BLIND_SUPERSEDED_PIPELINE_LOSS" in readiness
    assert "No human labels were accepted" in readiness

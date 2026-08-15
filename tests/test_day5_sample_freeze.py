import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONSENSUS = ROOT / "data/day5/day5_event_review_human_consensus.csv"
STRICT = ROOT / "data/day5/day5_strict_included_sample.csv"
SUPPORTING = ROOT / "data/day5/day5_supporting_included_sample.csv"
AUDIT = ROOT / "data/day5/day5_layer_membership_audit.csv"
FREEZE = ROOT / "data/day5/day5_replication_sample_freeze.json"
DUPLICATE = ROOT / "data/day5/day5_duplicate_vote_audit.json"
PREREGISTRATION = ROOT / "docs/research/DAY5_REPLICATION_PREREGISTRATION.md"


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_frozen_layer_membership_counts_and_subset_are_deterministic():
    audit = read_csv(AUDIT)
    assert len(audit) == 75
    assert Counter(row["pre_review_layer"] for row in audit) == Counter(
        {"strict": 34, "supporting_only": 41}
    )
    assert len({row["review_observation_id"] for row in audit}) == 75
    strict = read_csv(STRICT)
    supporting = read_csv(SUPPORTING)
    strict_ids = {row["review_observation_id"] for row in strict}
    supporting_ids = {row["review_observation_id"] for row in supporting}
    assert strict_ids <= supporting_ids
    assert (len(strict), len({r["source_event_cluster_id"] for r in strict}), len({r["normalized_borrower"] for r in strict})) == (31, 31, 16)
    assert (len(supporting), len({r["source_event_cluster_id"] for r in supporting}), len({r["normalized_borrower"] for r in supporting})) == (67, 67, 33)


def test_human_consensus_only_removes_and_never_promotes_or_replaces():
    consensus = read_csv(CONSENSUS)
    audit = {row["review_observation_id"]: row for row in read_csv(AUDIT)}
    yes_ids = {row["review_observation_id"] for row in consensus if row["include_for_replication"] == "yes"}
    supporting_ids = {row["review_observation_id"] for row in read_csv(SUPPORTING)}
    strict_ids = {row["review_observation_id"] for row in read_csv(STRICT)}
    assert supporting_ids == yes_ids
    assert all(audit[value]["pre_review_layer"] == "strict" for value in strict_ids)
    assert all(audit[value]["human_include_for_replication"] == "yes" for value in supporting_ids)
    assert not any(
        row["pre_review_layer"] == "supporting_only"
        and row["included_in_strict_sample"] == "True"
        for row in audit.values()
    )
    assert all(row["retained_in_audit_denominator"] == "True" for row in audit.values())


def test_frozen_sample_hashes_preregistration_and_duplicate_guard():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["sha256"]["strict_included_sample"] == sha256(STRICT)
    assert freeze["sha256"]["supporting_included_sample"] == sha256(SUPPORTING)
    assert freeze["sha256"]["final_preregistration"] == sha256(PREREGISTRATION)
    assert freeze["sha256"]["duplicate_vote_audit"] == sha256(DUPLICATE)
    duplicate = json.loads(DUPLICATE.read_text(encoding="utf-8"))
    assert duplicate["status"] == "pass_no_duplicate_independent_vote"
    assert duplicate["independent_vote_blocker_count"] == 0
    assert freeze["power_guard_pre_structural"]["guaranteed_underpowered_before_structural_review"] is False


def test_sample_files_contain_no_target_current_or_valuation_fields():
    for path in (STRICT, SUPPORTING, AUDIT):
        rows = read_csv(path)
        headers = [field.lower() for field in rows[0]]
        assert not any("target_current" in field for field in headers)
        assert not any(
            token in field
            for field in headers
            for token in ("principal", "cost", "fair_value", "mark", "prediction", "error", "return")
        )


def test_membership_key_remains_gitignored_and_untracked():
    key = "private/day5/day5_event_review_key.json"
    assert subprocess.run(["git", "check-ignore", "-q", key], cwd=ROOT).returncode == 0
    assert subprocess.run(
        ["git", "ls-files", "--error-unmatch", key], cwd=ROOT,
        capture_output=True,
    ).returncode != 0

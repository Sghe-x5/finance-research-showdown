import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLIND = ROOT / "data/day5/day5_event_review_blind.csv"
CONSENSUS = ROOT / "data/day5/day5_event_review_human_consensus.csv"
FREEZE = ROOT / "data/day5/day5_phase_a_event_review_freeze.json"
EXPECTED_CONSENSUS_SHA = "aef9a7d0e5fc89ef9e6d019f0ea0f1f09495089fcad74590e4747b4e27c2902b"
REVIEW_CHECKS = (
    "source_temporal_same_facility",
    "source_to_target_prior_same_facility",
    "source_aggregation_valid",
    "target_prior_aggregation_valid",
)
REVIEW_FIELDS = (*REVIEW_CHECKS, "include_for_replication", "review_notes")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def mechanical(row):
    values = [row[field] for field in REVIEW_CHECKS]
    return "no" if "no" in values else ("uncertain" if "uncertain" in values else "yes")


def test_consensus_hash_ids_order_and_counts_are_frozen():
    assert sha256(CONSENSUS) == EXPECTED_CONSENSUS_SHA
    blind_header, blind = read(BLIND)
    consensus_header, consensus = read(CONSENSUS)
    assert blind_header == consensus_header
    assert len(consensus) == 75
    ids = [row["review_observation_id"] for row in consensus]
    assert len(set(ids)) == 75
    assert ids == [row["review_observation_id"] for row in blind]
    assert Counter(row["include_for_replication"] for row in consensus) == Counter(
        {"yes": 67, "uncertain": 7, "no": 1}
    )


def test_consensus_nonreview_fields_and_mechanical_inclusion_are_unchanged():
    header, blind = read(BLIND)
    _, consensus = read(CONSENSUS)
    nonreview = [field for field in header if field not in REVIEW_FIELDS]
    assert all(
        all(left[field] == right[field] for field in nonreview)
        for left, right in zip(blind, consensus)
    )
    assert all(mechanical(row) == row["include_for_replication"] for row in consensus)


def test_phase_a_record_precedes_membership_and_outcome_access():
    record = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert record["consensus_sha256"] == EXPECTED_CONSENSUS_SHA
    assert len(record["ordered_review_observation_ids"]) == 75
    assert record["checks"]["private_layer_membership_key_opened"] is False
    assert record["checks"]["target_current_data_opened"] is False
    assert record["checks"]["human_labels_or_notes_changed"] is False

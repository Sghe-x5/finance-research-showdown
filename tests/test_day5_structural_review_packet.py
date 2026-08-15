import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "data/day5/day5_target_current_structural_review_blind.csv"
META = ROOT / "data/day5/day5_target_current_structural_review_meta.json"
FROZEN = ROOT / "data/day5/day5_supporting_included_sample.csv"
PRIVATE_KEY = ROOT / "private/day5/day5_structural_review_evidence_key.json"
REVIEW_FIELDS = (
    "target_current_same_facility",
    "target_current_aggregation_valid",
    "position_status",
    "structural_notes",
)
FORBIDDEN_HEADER_TOKENS = (
    "principal", "cost", "fair_value", "fv_par", "mark", "prediction",
    "error", "return", "accession", "url", "provenance", "phase_a",
    "include_for_replication", "adjudicat", "consensus", "pre_review_layer",
    "strict", "supporting",
)


def rows(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_structural_packet_exactly_matches_frozen_supporting_ids_and_order():
    packet = rows(PACKET)
    frozen = rows(FROZEN)
    assert len(packet) == 67
    assert [row["review_observation_id"] for row in packet] == [
        row["review_observation_id"] for row in frozen
    ]
    assert [row["source_event_cluster_id"] for row in packet] == [
        row["source_event_cluster_id"] for row in frozen
    ]
    assert len({row["source_event_cluster_id"] for row in packet}) == 67
    assert all(row[field] == "" for row in packet for field in REVIEW_FIELDS)


def test_structural_packet_hides_layers_phase_a_and_all_valuation_fields():
    with PACKET.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        packet = list(reader)
    assert not any(
        token in field.casefold()
        for field in fields for token in FORBIDDEN_HEADER_TOKENS
    )
    assert not any(field.startswith(("phase_a_", "reviewer_")) for field in fields)
    assert not any(
        re.search(r"https?://|www\.|sec\.gov|/Archives/edgar|\b\d{10}-\d{2}-\d{6}\b", value, re.IGNORECASE)
        for row in packet for value in row.values() if value
    )


def test_structural_meta_and_private_evidence_boundary_are_locked():
    meta = json.loads(META.read_text(encoding="utf-8"))
    assert sha256(PACKET) == meta["structural_packet_sha256"]
    assert meta["review_observations"] == 67
    assert meta["source_event_clusters"] == 67
    assert meta["exact_frozen_id_order_match"] is True
    assert meta["strict_supporting_membership_exposed"] is False
    assert meta["numeric_valuation_columns_projected_or_used"] is False
    assert meta["phase_a_labels_notes_or_inclusion_in_packet"] is False
    assert meta["numeric_evaluation_run"] is False
    assert meta["numeric_reveal_authorized"] is False
    assert meta["structurally_mapped_rows"] == 50
    assert meta["structurally_unmapped_rows_retained"] == 17
    assert PRIVATE_KEY.exists()
    assert sha256(PRIVATE_KEY) == meta["private_evidence_key_sha256"]
    assert subprocess.run(
        ["git", "check-ignore", "-q", str(PRIVATE_KEY.relative_to(ROOT))],
        cwd=ROOT,
    ).returncode == 0
    assert subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(PRIVATE_KEY.relative_to(ROOT))],
        cwd=ROOT,
        capture_output=True,
    ).returncode != 0


def test_opaque_evidence_ids_are_non_navigable_and_unique():
    packet = rows(PACKET)
    current = [row["target_current_evidence_id"] for row in packet if row["target_current_evidence_id"]]
    assert len(current) == 50
    assert len(current) == len(set(current))
    assert all(re.fullmatch(r"D5SE_[0-9a-f]{24}", value) for value in current)
    assert all(re.fullmatch(r"EVID_[0-9a-f]{28}", row["target_prior_evidence_id"]) for row in packet)


def test_later_numeric_result_has_separate_authorization_and_no_tag():
    result = ROOT / "data/day5/day5_replication_results.json"
    if result.exists():
        assert (ROOT / "data/day5/day5_reveal_authorization.json").exists()
        assert (ROOT / "data/day5/day5_structural_mapping_freeze.json").exists()
    tags = subprocess.check_output(["git", "tag", "--list", "*day5*"], cwd=ROOT, text=True)
    assert tags.strip() == ""

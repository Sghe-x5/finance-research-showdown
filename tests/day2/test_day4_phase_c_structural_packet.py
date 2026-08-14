import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path


PACKET = Path("data/day4/target_current_structural_review_blind.csv")
META = Path("data/day4/target_current_structural_review_meta.json")
FROZEN = Path("data/day4/confirmatory_included_sample.csv")
PRIVATE_KEY = Path("private/day4/structural_review_evidence_key.json")
REVIEW_FIELDS = (
    "target_current_same_facility",
    "target_current_aggregation_valid",
    "position_status",
    "structural_notes",
)
FORBIDDEN_HEADER_TOKENS = (
    "principal",
    "cost",
    "fair_value",
    "fv_par",
    "mark",
    "prediction",
    "error",
    "return",
    "accession",
    "url",
    "provenance",
    "phase_a",
    "include_for_confirmatory",
    "adjudicat",
    "consensus_",
)


def rows(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_phase_c_packet_has_exact_frozen_rows_clusters_order_and_blank_labels():
    packet = rows(PACKET)
    frozen = rows(FROZEN)
    assert len(packet) == 37
    assert [row["review_observation_id"] for row in packet] == [
        row["review_observation_id"] for row in frozen
    ]
    assert [row["source_event_cluster_id"] for row in packet] == [
        row["source_event_cluster_id"] for row in frozen
    ]
    assert len({row["source_event_cluster_id"] for row in packet}) == 34
    assert all(not row[field] for row in packet for field in REVIEW_FIELDS)


def test_phase_c_packet_contains_only_structural_nonvaluation_fields():
    with PACKET.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        packet = list(reader)
    assert not any(
        token in field.casefold()
        for field in fields
        for token in FORBIDDEN_HEADER_TOKENS
    )
    assert not any(
        re.search(r"https?://|www\.|sec\.gov|/Archives/edgar|\b\d{10}-\d{2}-\d{6}\b", value)
        for row in packet
        for value in row.values()
        if value
    )
    assert not any(field.startswith(("reviewer_", "phase_a_")) for field in fields)


def test_phase_c_metadata_and_private_evidence_boundary_are_locked():
    meta = json.loads(META.read_text(encoding="utf-8"))
    assert digest(PACKET) == meta["structural_packet_sha256"]
    assert meta["review_observations"] == 37
    assert meta["source_event_clusters"] == 34
    assert meta["exact_frozen_id_order_match"] is True
    assert meta["numeric_valuation_columns_projected_or_used"] is False
    assert meta["numeric_evaluation_run"] is False
    assert meta["numeric_reveal_authorized"] is False
    assert meta["phase_a_labels_notes_or_inclusion_in_packet"] is False
    assert meta["structurally_mapped_rows"] == 36
    assert meta["structurally_unmapped_rows_retained"] == 1
    assert PRIVATE_KEY.exists()
    assert digest(PRIVATE_KEY) == meta["private_evidence_key_sha256"]
    assert subprocess.run(
        ["git", "check-ignore", "-q", str(PRIVATE_KEY)], check=False
    ).returncode == 0
    assert subprocess.check_output(
        ["git", "ls-files", "private/day4"], text=True
    ).strip() == ""


def test_structural_packet_opaque_evidence_ids_are_non_navigable():
    packet = rows(PACKET)
    current_ids = [
        row["target_current_evidence_id"]
        for row in packet
        if row["target_current_evidence_id"]
    ]
    assert len(current_ids) == 36
    assert len(current_ids) == len(set(current_ids))
    assert all(re.fullmatch(r"D4SE_[0-9a-f]{24}", value) for value in current_ids)
    assert all(
        re.fullmatch(r"EVID_[0-9a-f]{28}", row["target_prior_evidence_id"])
        for row in packet
    )

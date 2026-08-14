#!/usr/bin/env python3
"""Create the clean-review v2 packet without navigable SEC evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import json
import re
import secrets
from collections import Counter
from pathlib import Path


EXPECTED_OLD_PACKET_SHA256 = "502593065880ca0325910e59e46e126f7154ee162646c885bb953bfc5ffd8153"
EXPECTED_ROWS = 40
EXPECTED_CLUSTERS = 37

REVIEW_FIELDS = (
    "source_temporal_same_facility",
    "source_to_target_prior_same_facility",
    "source_aggregation_valid",
    "target_prior_aggregation_valid",
    "include_for_confirmatory_test",
    "review_notes",
)

BASE_FIELDS = (
    "review_observation_id",
    "source_event_cluster_id",
    "period_end",
    "report_period_label",
    "normalized_borrower",
    "source_ticker",
    "target_ticker",
    "source_manager",
    "target_manager",
    "manager_relationship",
)

SAFE_SIDE_FIELDS = (
    "raw_identifier",
    "facility_type",
    "lien",
    "currency",
    "reference_rate",
    "spread",
    "maturity",
    "funded_status",
    "acquisition_date",
    "constituent_raw_identifiers_json",
    "aggregation_lot_count",
    "accepted_timestamp_utc",
)

OUTPUT_FIELDS = (
    *BASE_FIELDS,
    *(f"{side}_{field}" for side in ("source_current", "source_prior", "target_prior") for field in SAFE_SIDE_FIELDS),
    "source_current_evidence_id",
    "source_prior_evidence_id",
    "target_prior_evidence_id",
    "source_results_public_timestamp_utc",
    "source_mark_public_timestamp_utc",
    "source_information_timestamp_utc",
    "source_prior_public_timestamp_utc",
    "target_prior_public_timestamp_utc",
    "target_cutoff_timestamp_utc",
    "source_mark_public_evidence",
    "source_timing_evidence_id",
    "source_timing_evidence_statement",
    "target_cutoff_evidence_id",
    "target_cutoff_evidence_statement",
    *REVIEW_FIELDS,
)

UNSAFE_SOURCE_FIELDS = {
    "source_current_filing_evidence_url",
    "source_current_raw_provenance_json",
    "source_prior_filing_evidence_url",
    "source_prior_raw_provenance_json",
    "target_prior_filing_evidence_url",
    "target_prior_raw_provenance_json",
    "source_results_evidence_url",
    "source_results_verification_evidence",
    "source_prior_reporting_evidence_url",
    "target_prior_reporting_evidence_url",
    "target_cutoff_evidence_url",
    "target_cutoff_verification_evidence",
}

FORBIDDEN_HEADER_TOKENS = ("url", "accession", "provenance", "archive", "sec_path")
URL_RE = re.compile(r"(?:https?://|www\.|/Archives/|sec\.gov)", re.IGNORECASE)
ACCESSION_RE = re.compile(r"\b\d{10}-\d{2}-\d{6}\b")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(values) -> str:
    payload = json.dumps(sorted(set(values)), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def ordered_sha256(values) -> str:
    payload = json.dumps(list(values), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def evidence_id(secret: str, scope: str, payload: dict) -> str:
    message = json.dumps(
        {"scope": scope, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hmac.new(bytes.fromhex(secret), message, hashlib.sha256).hexdigest()
    return "EVID_" + digest[:28]


def add_private_mapping(mappings: dict, opaque_id: str, scope: str, payload: dict) -> None:
    value = {"scope": scope, "underlying_evidence": payload}
    previous = mappings.setdefault(opaque_id, value)
    if previous != value:
        raise RuntimeError("Opaque evidence-ID collision")


def load_or_create_secret(private_path: Path) -> str:
    if private_path.exists():
        existing = json.loads(private_path.read_text(encoding="utf-8"))
        secret = existing.get("hmac_secret_hex", "")
        if len(secret) != 64:
            raise RuntimeError("Existing private evidence key has an invalid secret")
        return secret
    return secrets.token_hex(32)


def safe_side(row: dict[str, str], side: str) -> dict[str, str]:
    return {
        f"{side}_{field}": row[f"{side}_{field}"]
        for field in SAFE_SIDE_FIELDS
    }


def build(old_rows: list[dict[str, str]], secret: str) -> tuple[list[dict], dict]:
    clean = []
    mappings = {}
    assignments = []
    for old in old_rows:
        side_payloads = {
            side: {
                "filing_evidence_url": old[f"{side}_filing_evidence_url"],
                "raw_provenance_json": old[f"{side}_raw_provenance_json"],
            }
            for side in ("source_current", "source_prior", "target_prior")
        }
        side_ids = {}
        for side, payload in side_payloads.items():
            opaque_id = evidence_id(secret, side, payload)
            add_private_mapping(mappings, opaque_id, side, payload)
            side_ids[side] = opaque_id

        source_timing_payload = {
            "source_results_evidence_url": old["source_results_evidence_url"],
            "source_results_verification_evidence": old[
                "source_results_verification_evidence"
            ],
            "source_prior_reporting_evidence_url": old[
                "source_prior_reporting_evidence_url"
            ],
        }
        source_timing_id = evidence_id(secret, "source_timing", source_timing_payload)
        add_private_mapping(
            mappings, source_timing_id, "source_timing", source_timing_payload
        )

        target_cutoff_payload = {
            "target_prior_reporting_evidence_url": old[
                "target_prior_reporting_evidence_url"
            ],
            "target_cutoff_evidence_url": old["target_cutoff_evidence_url"],
            "target_cutoff_verification_evidence": old[
                "target_cutoff_verification_evidence"
            ],
        }
        target_cutoff_id = evidence_id(secret, "target_cutoff", target_cutoff_payload)
        add_private_mapping(
            mappings, target_cutoff_id, "target_cutoff", target_cutoff_payload
        )

        new = {field: old[field] for field in BASE_FIELDS}
        for side in ("source_current", "source_prior", "target_prior"):
            new.update(safe_side(old, side))
        new.update({
            "source_current_evidence_id": side_ids["source_current"],
            "source_prior_evidence_id": side_ids["source_prior"],
            "target_prior_evidence_id": side_ids["target_prior"],
            "source_results_public_timestamp_utc": old[
                "source_results_public_timestamp_utc"
            ],
            "source_mark_public_timestamp_utc": old[
                "source_mark_public_timestamp_utc"
            ],
            "source_information_timestamp_utc": old[
                "source_information_timestamp_utc"
            ],
            "source_prior_public_timestamp_utc": old[
                "source_prior_public_timestamp_utc"
            ],
            "target_prior_public_timestamp_utc": old[
                "target_prior_public_timestamp_utc"
            ],
            "target_cutoff_timestamp_utc": old["target_cutoff_timestamp_utc"],
            "source_mark_public_evidence": old["source_mark_public_evidence"],
            "source_timing_evidence_id": source_timing_id,
            "source_timing_evidence_statement": (
                "Timing verified against locked source reporting and facility-publication "
                "records; navigable evidence withheld from clean reviewers."
            ),
            "target_cutoff_evidence_id": target_cutoff_id,
            "target_cutoff_evidence_statement": (
                "Cutoff verified against the locked target reporting-order record; "
                "navigable evidence withheld from clean reviewers."
            ),
            **{field: old[field] for field in REVIEW_FIELDS},
        })
        clean.append(new)
        assignments.append({
            "review_observation_id": old["review_observation_id"],
            "source_current_evidence_id": side_ids["source_current"],
            "source_prior_evidence_id": side_ids["source_prior"],
            "target_prior_evidence_id": side_ids["target_prior"],
            "source_timing_evidence_id": source_timing_id,
            "target_cutoff_evidence_id": target_cutoff_id,
        })
    private_payload = {
        "status": "ignored_private_review_evidence_mapping",
        "hmac_secret_hex": secret,
        "mappings": mappings,
        "row_evidence_assignments": assignments,
    }
    return clean, private_payload


def validate(old_rows: list[dict], clean_rows: list[dict]) -> None:
    if len(old_rows) != EXPECTED_ROWS or len(clean_rows) != EXPECTED_ROWS:
        raise RuntimeError("Sanitization changed the 40-row packet")
    old_ids = [row["review_observation_id"] for row in old_rows]
    new_ids = [row["review_observation_id"] for row in clean_rows]
    old_clusters = [row["source_event_cluster_id"] for row in old_rows]
    new_clusters = [row["source_event_cluster_id"] for row in clean_rows]
    if old_ids != new_ids or old_clusters != new_clusters:
        raise RuntimeError("Sanitization changed row order, observation IDs, or cluster IDs")
    if len(set(new_clusters)) != EXPECTED_CLUSTERS:
        raise RuntimeError("Sanitized packet does not contain 37 clusters")
    headers = set(OUTPUT_FIELDS)
    if headers & UNSAFE_SOURCE_FIELDS:
        raise RuntimeError("Explicit unsafe evidence field remains")
    if any(token in header.lower() for header in headers for token in FORBIDDEN_HEADER_TOKENS):
        raise RuntimeError("Navigable-evidence token remains in a v2 header")
    if any("target_current" in header.lower() for header in headers):
        raise RuntimeError("Target-current field remains in v2")
    for row in clean_rows:
        for field, value in row.items():
            if URL_RE.search(value or "") or ACCESSION_RE.search(value or ""):
                raise RuntimeError(f"Navigable evidence leaked into {field}")
        if any(row[field] for field in REVIEW_FIELDS):
            raise RuntimeError("Human-review labels must remain blank")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", type=Path, default=Path("data/day4/confirmatory_event_review_blind.csv")
    )
    parser.add_argument(
        "--old-meta", type=Path, default=Path("data/day4/confirmatory_event_review_meta.json")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/day4/confirmatory_event_review_blind_v2.csv")
    )
    parser.add_argument(
        "--metadata", type=Path, default=Path("data/day4/confirmatory_event_review_blind_v2_meta.json")
    )
    parser.add_argument(
        "--private-key", type=Path, default=Path("private/day4/review_evidence_key.json")
    )
    args = parser.parse_args()

    if sha256_file(args.input) != EXPECTED_OLD_PACKET_SHA256:
        raise RuntimeError("Old packet SHA-256 differs from the audited Day 4 input")
    old_rows = read_csv(args.input)
    old_meta = json.loads(args.old_meta.read_text(encoding="utf-8"))
    secret = load_or_create_secret(args.private_key)
    clean_rows, private_payload = build(old_rows, secret)
    validate(old_rows, clean_rows)

    args.private_key.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.private_key, private_payload)
    write_csv(args.output, clean_rows)

    old_observation_ids = [row["review_observation_id"] for row in old_rows]
    new_observation_ids = [row["review_observation_id"] for row in clean_rows]
    old_cluster_ids = [row["source_event_cluster_id"] for row in old_rows]
    new_cluster_ids = [row["source_event_cluster_id"] for row in clean_rows]
    periods = Counter(row["report_period_label"] for row in clean_rows)
    metadata = {
        "status": "clean_reviewer_packet_unlabeled",
        "supersedes": "data/day4/confirmatory_event_review_blind.csv",
        "supersession_reason": "indirect_outcome_linkage_risk",
        "old_packet_sha256": sha256_file(args.input),
        "sanitized_packet_sha256": sha256_file(args.output),
        "private_evidence_key_sha256": sha256_file(args.private_key),
        "review_observations": len(clean_rows),
        "independent_source_event_clusters": len(set(new_cluster_ids)),
        "row_order_unchanged": old_observation_ids == new_observation_ids,
        "old_ordered_observation_ids_sha256": ordered_sha256(old_observation_ids),
        "new_ordered_observation_ids_sha256": ordered_sha256(new_observation_ids),
        "old_observation_id_set_sha256": canonical_sha256(old_observation_ids),
        "new_observation_id_set_sha256": canonical_sha256(new_observation_ids),
        "old_cluster_id_set_sha256": canonical_sha256(old_cluster_ids),
        "new_cluster_id_set_sha256": canonical_sha256(new_cluster_ids),
        "period_observation_counts": dict(sorted(periods.items())),
        "selection_rules_unchanged": True,
        "source_target_relationships_unchanged": True,
        "human_review_fields_blank": True,
        "opaque_evidence_ids_only": True,
        "no_url_columns": True,
        "no_accession_or_document_identifier_columns": True,
        "no_raw_provenance": True,
        "no_source_or_target_numeric_marks": True,
        "no_principal_cost_or_fair_value": True,
        "no_target_current_fields": True,
        "target_outcomes_opened": False,
        "freeze_authorized": False,
        "reveal_authorized": False,
        "results_tag_authorized": False,
        "output_schema": list(OUTPUT_FIELDS),
    }
    write_json(args.metadata, metadata)

    old_meta.update({
        "status": "superseded_indirect_outcome_linkage_risk",
        "superseded_by": str(args.output),
        "supersession_reason": (
            "Direct filing and reporting links can expose source marks or target-current outcomes"
        ),
    })
    write_json(args.old_meta, old_meta)
    print(json.dumps({
        "sanitized_packet_sha256": metadata["sanitized_packet_sha256"],
        "private_evidence_key_sha256": metadata["private_evidence_key_sha256"],
        "rows": len(clean_rows),
        "clusters": len(set(new_cluster_ids)),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

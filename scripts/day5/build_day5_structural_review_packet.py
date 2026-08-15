#!/usr/bin/env python3
"""Build the Day 5 Phase C packet without projecting valuation columns."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


PHASE_B_COMMIT = "f7ee622aa256dd4ba136dc8de2b477076d8a0229"
SUPPORTING_SAMPLE_SHA256 = "d4890bcbce1f8880cb56ca9ffe86071d3514064d4ff8488c685ef5f3cb62b50f"
EVENT_PACKET_SHA256 = "4f7c0e8941a321a7e95d5395ce60182f380a063933dc2f2c8dc5373771172625"
HISTORICAL_FACILITIES_SHA256 = "535ec3a3e8e0e986881dbaa417cba441dd913be6186224ce166da6caea523a71"
NEW_FACILITIES_SHA256 = "4a02fc27bba48c48ded40e96d231b1487659b7733f60326796da2e7e67896925"
EXPECTED_ROWS = 67
EXPECTED_CLUSTERS = 67

STRUCTURAL_ATTRIBUTES = (
    "facility_type",
    "lien",
    "currency",
    "reference_rate",
    "spread",
    "maturity",
    "funded_status",
)

FACILITY_PROJECTION = (
    "economic_facility_id",
    "archive_id",
    "adsh",
    "cik",
    "ticker",
    "period_end",
    "observation_date",
    "is_current_period",
    "investment_identifier",
    "borrower_norm",
    *STRUCTURAL_ATTRIBUTES,
    "lot_count",
)

OUTPUT_FIELDS = (
    "review_observation_id",
    "source_event_cluster_id",
    "normalized_borrower",
    "source_ticker",
    "target_ticker",
    "target_prior_identifier",
    *(f"target_prior_{field}" for field in STRUCTURAL_ATTRIBUTES),
    "target_prior_constituent_descriptions",
    "target_prior_aggregation_lot_count",
    "target_prior_evidence_id",
    "target_current_identifier",
    *(f"target_current_{field}" for field in STRUCTURAL_ATTRIBUTES),
    "target_current_constituent_descriptions",
    "target_current_aggregation_lot_count",
    "target_current_evidence_id",
    "target_current_same_facility",
    "target_current_aggregation_valid",
    "position_status",
    "structural_notes",
)

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
    "include_for_replication",
    "adjudicat",
    "consensus",
    "pre_review_layer",
    "strict",
    "supporting",
)

NAVIGABLE_RE = re.compile(
    r"https?://|www\.|sec\.gov|/Archives/edgar|\b\d{10}-\d{2}-\d{6}\b",
    re.IGNORECASE,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_sha(path: Path, expected: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"Input SHA-256 mismatch for {path}: {actual}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def projected_current_facilities(
    paths: list[Path],
    wanted_keys: set[tuple[str, str, str]],
) -> dict[tuple[str, str, str], list[dict[str, str]]]:
    """Read only structural cells; valuation cells never enter a Python dict."""
    found: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    seen_ids = set()
    for path in paths:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            missing = set(FACILITY_PROJECTION) - set(header)
            if missing:
                raise RuntimeError(f"Facility source lacks structural columns: {missing}")
            indexes = {field: header.index(field) for field in FACILITY_PROJECTION}
            for values in reader:
                key = (
                    values[indexes["ticker"]],
                    values[indexes["period_end"]],
                    values[indexes["borrower_norm"]],
                )
                if key not in wanted_keys or values[indexes["is_current_period"]] != "True":
                    continue
                projected = {field: values[index] for field, index in indexes.items()}
                facility_id = projected["economic_facility_id"]
                if facility_id in seen_ids:
                    continue
                seen_ids.add(facility_id)
                found[key].append(projected)
    return found


def normalized_text(value: str) -> str:
    return " ".join((value or "").casefold().split())


def select_structural_candidate(
    prior: dict[str, str],
    candidates: list[dict[str, str]],
) -> tuple[dict[str, str] | None, str]:
    if not candidates:
        return None, "no_exact_borrower_current_candidate"
    if len(candidates) == 1:
        return candidates[0], "single_exact_borrower_current_candidate"
    prior_identifier = normalized_text(prior["target_prior_raw_identifier"])
    exact_identifier = [
        row for row in candidates
        if normalized_text(row["investment_identifier"]) == prior_identifier
    ]
    if len(exact_identifier) == 1:
        return exact_identifier[0], "unique_exact_identifier_match"
    prior_signature = tuple(
        prior[f"target_prior_{field}"] for field in STRUCTURAL_ATTRIBUTES
    )
    exact_signature = [
        row for row in candidates
        if tuple(row[field] for field in STRUCTURAL_ATTRIBUTES) == prior_signature
    ]
    if len(exact_signature) == 1:
        return exact_signature[0], "unique_exact_structural_signature_match"
    return None, "ambiguous_exact_borrower_current_candidates"


def constituent_descriptions(identifier: str) -> str:
    values = sorted({
        value.strip() for value in (identifier or "").split(" | ") if value.strip()
    })
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"))


def opaque_evidence_id(observation_id: str, facility_id: str) -> str:
    material = f"day5-phase-c\x1f{observation_id}\x1f{facility_id}".encode("utf-8")
    return "D5SE_" + hashlib.sha256(material).hexdigest()[:24]


def build_rows(
    included: list[dict[str, str]],
    packet_by_id: dict[str, dict[str, str]],
    current_by_key: dict[tuple[str, str, str], list[dict[str, str]]],
) -> tuple[list[dict[str, str]], dict]:
    output = []
    mappings = {}
    reasons = Counter()
    for frozen in included:
        observation_id = frozen["review_observation_id"]
        prior = packet_by_id[observation_id]
        key = (
            frozen["target_ticker"],
            frozen["period_end"],
            frozen["normalized_borrower"],
        )
        candidate, reason = select_structural_candidate(prior, current_by_key[key])
        reasons[reason] += 1
        row = {
            "review_observation_id": observation_id,
            "source_event_cluster_id": frozen["source_event_cluster_id"],
            "normalized_borrower": frozen["normalized_borrower"],
            "source_ticker": frozen["source_ticker"],
            "target_ticker": frozen["target_ticker"],
            "target_prior_identifier": prior["target_prior_raw_identifier"],
            **{
                f"target_prior_{field}": prior[f"target_prior_{field}"]
                for field in STRUCTURAL_ATTRIBUTES
            },
            "target_prior_constituent_descriptions": prior[
                "target_prior_constituent_descriptions_json"
            ],
            "target_prior_aggregation_lot_count": prior[
                "target_prior_aggregation_lot_count"
            ],
            "target_prior_evidence_id": prior["target_prior_evidence_id"],
            **{field: "" for field in REVIEW_FIELDS},
        }
        private_entry = {
            "review_observation_id": observation_id,
            "selection_reason": reason,
            "candidate_facility_ids": [
                value["economic_facility_id"] for value in current_by_key[key]
            ],
        }
        if candidate is None:
            row.update({
                "target_current_identifier": "",
                **{f"target_current_{field}": "" for field in STRUCTURAL_ATTRIBUTES},
                "target_current_constituent_descriptions": "[]",
                "target_current_aggregation_lot_count": "",
                "target_current_evidence_id": "",
            })
        else:
            evidence_id = opaque_evidence_id(observation_id, candidate["economic_facility_id"])
            row.update({
                "target_current_identifier": candidate["investment_identifier"],
                **{
                    f"target_current_{field}": candidate[field]
                    for field in STRUCTURAL_ATTRIBUTES
                },
                "target_current_constituent_descriptions": constituent_descriptions(
                    candidate["investment_identifier"]
                ),
                "target_current_aggregation_lot_count": candidate["lot_count"],
                "target_current_evidence_id": evidence_id,
            })
            private_entry.update({
                "target_current_evidence_id": evidence_id,
                "selected_economic_facility_id": candidate["economic_facility_id"],
                "archive_id": candidate["archive_id"],
                "cik": candidate["cik"],
                "adsh": candidate["adsh"],
            })
        mappings[observation_id] = private_entry
        output.append({field: row[field] for field in OUTPUT_FIELDS})
    return output, {
        "schema_version": "day5_phase_c_structural_evidence_key_v1",
        "phase_b_sample_freeze_commit": PHASE_B_COMMIT,
        "review_observation_mapping": mappings,
        "mapping_reason_counts": dict(sorted(reasons.items())),
    }


def ordered_sha256(values) -> str:
    payload = json.dumps(list(values), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate(rows: list[dict[str, str]], included: list[dict[str, str]]) -> None:
    if len(rows) != EXPECTED_ROWS:
        raise RuntimeError(f"Expected {EXPECTED_ROWS} structural rows, found {len(rows)}")
    row_ids = [row["review_observation_id"] for row in rows]
    frozen_ids = [row["review_observation_id"] for row in included]
    if row_ids != frozen_ids or len(row_ids) != len(set(row_ids)):
        raise RuntimeError("Structural packet IDs/order differ from frozen SUPPORTING sample")
    if len({row["source_event_cluster_id"] for row in rows}) != EXPECTED_CLUSTERS:
        raise RuntimeError("Structural source-event cluster count changed")
    forbidden = [
        field for field in OUTPUT_FIELDS
        if any(token in field.casefold() for token in FORBIDDEN_HEADER_TOKENS)
    ]
    if forbidden:
        raise RuntimeError(f"Prohibited structural-packet headers: {forbidden}")
    if any(row[field] for row in rows for field in REVIEW_FIELDS):
        raise RuntimeError("Structural reviewer fields are not blank")
    if any(
        NAVIGABLE_RE.search(value)
        for row in rows for value in row.values() if value
    ):
        raise RuntimeError("Navigable filing evidence leaked into structural packet")


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--supporting-sample", type=Path, default=Path("data/day5/day5_supporting_included_sample.csv"))
    parser.add_argument("--event-packet", type=Path, default=Path("data/day5/day5_event_review_blind.csv"))
    parser.add_argument("--historical-facilities", type=Path, default=Path("/private/tmp/finance-day3-sec-cache/bdc_facilities_all_agg.csv"))
    parser.add_argument("--new-facilities", type=Path, default=Path("/private/tmp/finance-day5-sec-cache/bdc_facilities_2026_new_agg.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/day5/day5_target_current_structural_review_blind.csv"))
    parser.add_argument("--metadata", type=Path, default=Path("data/day5/day5_target_current_structural_review_meta.json"))
    parser.add_argument("--private-evidence-key", type=Path, default=Path("private/day5/day5_structural_review_evidence_key.json"))
    args = parser.parse_args()

    assert_sha(args.supporting_sample, SUPPORTING_SAMPLE_SHA256)
    assert_sha(args.event_packet, EVENT_PACKET_SHA256)
    assert_sha(args.historical_facilities, HISTORICAL_FACILITIES_SHA256)
    assert_sha(args.new_facilities, NEW_FACILITIES_SHA256)
    included = read_csv(args.supporting_sample)
    event_packet = read_csv(args.event_packet)
    packet_by_id = {row["review_observation_id"]: row for row in event_packet}
    if any(row["review_observation_id"] not in packet_by_id for row in included):
        raise RuntimeError("Frozen SUPPORTING ID is missing from clean event packet")
    wanted = {
        (row["target_ticker"], row["period_end"], row["normalized_borrower"])
        for row in included
    }
    current = projected_current_facilities(
        [args.historical_facilities, args.new_facilities], wanted
    )
    rows, private_key = build_rows(included, packet_by_id, current)
    validate(rows, included)
    write_csv(args.output, rows)
    write_json(args.private_evidence_key, private_key)

    packet_sha = sha256_file(args.output)
    private_sha = sha256_file(args.private_evidence_key)
    frozen_ids = [row["review_observation_id"] for row in included]
    meta = {
        "status": "phase_c_structural_review_packet_unlabeled",
        "phase_b_sample_freeze_commit": PHASE_B_COMMIT,
        "structural_packet_sha256": packet_sha,
        "review_observations": len(rows),
        "source_event_clusters": len({row["source_event_cluster_id"] for row in rows}),
        "ordered_observation_id_sha256": ordered_sha256(row["review_observation_id"] for row in rows),
        "ordered_frozen_observation_id_sha256": ordered_sha256(frozen_ids),
        "exact_frozen_id_order_match": True,
        "strict_supporting_membership_exposed": False,
        "structurally_mapped_rows": sum(bool(row["target_current_evidence_id"]) for row in rows),
        "structurally_unmapped_rows_retained": sum(not row["target_current_evidence_id"] for row in rows),
        "mapping_reason_counts": private_key["mapping_reason_counts"],
        "private_evidence_key_sha256": private_sha,
        "private_evidence_key_path": str(args.private_evidence_key),
        "private_evidence_key_tracked": False,
        "facility_reader_projection": list(FACILITY_PROJECTION),
        "numeric_valuation_columns_projected_or_used": False,
        "principal_cost_fair_value_or_ratio_in_packet": False,
        "source_movement_prediction_error_or_return_in_packet": False,
        "phase_a_labels_notes_or_inclusion_in_packet": False,
        "navigable_urls_accessions_or_raw_provenance_in_packet": False,
        "review_fields_blank": True,
        "numeric_reveal_authorized": False,
        "numeric_evaluation_run": False,
        "results_tag_authorized": False,
        "output_schema": list(OUTPUT_FIELDS),
        "input_sha256": {
            "supporting_included_sample": sha256_file(args.supporting_sample),
            "clean_event_packet": sha256_file(args.event_packet),
            "historical_economic_facility_v2": sha256_file(args.historical_facilities),
            "new_economic_facility_v2": sha256_file(args.new_facilities),
        },
    }
    write_json(args.metadata, meta)
    print(json.dumps({
        "packet": str(args.output),
        "sha256": packet_sha,
        "rows": len(rows),
        "clusters": meta["source_event_clusters"],
        "mapped": meta["structurally_mapped_rows"],
        "unmapped_retained": meta["structurally_unmapped_rows_retained"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

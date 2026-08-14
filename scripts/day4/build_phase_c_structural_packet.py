#!/usr/bin/env python3
"""Build the Phase C packet with target-current structure and no numeric marks.

The large economic-facility CSV is projected at the reader boundary. Numeric
valuation columns are never placed in a dict, compared, logged, or written.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


PHASE_B_COMMIT = "d27dec28cc361db03680820997b2d9e7e7463cda"
FACILITIES_SHA256 = "60aee6b26872b65a0845a58db286e3409518498532d2eb69d0ffc7c1d356bbec"
INCLUDED_SAMPLE_SHA256 = "011da2ab9ccc39f5c2530295fee1b555377f4a2b36a302e45183873af603a670"
SANITIZED_PACKET_SHA256 = "8d37ae3c2bbd9c4c4391c474e18347f9be5f15cf11056488a1bbbc11026f6db6"
EXPECTED_ROWS = 37
EXPECTED_CLUSTERS = 34

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
    "include_for_confirmatory",
    "adjudicat",
    "consensus_",
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
        raise RuntimeError(f"Input SHA-256 mismatch for {path}: {actual} != {expected}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def projected_current_facilities(
    path: Path,
    wanted_keys: set[tuple[str, str, str]],
) -> dict[tuple[str, str, str], list[dict[str, str]]]:
    """Project only structural columns before any target-current row is retained."""
    found: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        missing = set(FACILITY_PROJECTION) - set(header)
        if missing:
            raise RuntimeError(f"Facility source is missing projected columns: {missing}")
        indexes = {field: header.index(field) for field in FACILITY_PROJECTION}
        for values in reader:
            key = (
                values[indexes["ticker"]],
                values[indexes["period_end"]],
                values[indexes["borrower_norm"]],
            )
            if key not in wanted_keys or values[indexes["is_current_period"]] != "True":
                continue
            found[key].append({
                field: values[index]
                for field, index in indexes.items()
            })
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
    identifier_matches = [
        candidate for candidate in candidates
        if normalized_text(candidate["investment_identifier"]) == prior_identifier
    ]
    if len(identifier_matches) == 1:
        return identifier_matches[0], "unique_exact_identifier_match"
    prior_signature = tuple(
        prior[f"target_prior_{field}"] for field in STRUCTURAL_ATTRIBUTES
    )
    signature_matches = [
        candidate for candidate in candidates
        if tuple(candidate[field] for field in STRUCTURAL_ATTRIBUTES) == prior_signature
    ]
    if len(signature_matches) == 1:
        return signature_matches[0], "unique_exact_structural_signature_match"
    return None, "ambiguous_exact_borrower_current_candidates"


def constituent_descriptions(identifier: str) -> str:
    values = sorted({
        value.strip() for value in (identifier or "").split(" | ") if value.strip()
    })
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"))


def opaque_evidence_id(observation_id: str, facility_id: str) -> str:
    material = f"phase-c\x1f{observation_id}\x1f{facility_id}".encode("utf-8")
    return "D4SE_" + hashlib.sha256(material).hexdigest()[:24]


def build_rows(
    included: list[dict[str, str]],
    packet_by_id: dict[str, dict[str, str]],
    current_by_key: dict[tuple[str, str, str], list[dict[str, str]]],
) -> tuple[list[dict[str, str]], dict]:
    output = []
    private_mappings = {}
    mapping_reasons = Counter()
    for frozen in included:
        observation_id = frozen["review_observation_id"]
        prior = packet_by_id[observation_id]
        key = (
            frozen["target_ticker"],
            frozen["period_end"],
            frozen["normalized_borrower"],
        )
        candidate, reason = select_structural_candidate(prior, current_by_key[key])
        mapping_reasons[reason] += 1
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
                "target_prior_constituent_raw_identifiers_json"
            ],
            "target_prior_aggregation_lot_count": prior[
                "target_prior_aggregation_lot_count"
            ],
            "target_prior_evidence_id": prior["target_prior_evidence_id"],
            **{field: "" for field in REVIEW_FIELDS},
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
            evidence_id = opaque_evidence_id(
                observation_id,
                candidate["economic_facility_id"],
            )
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
            private_mappings[evidence_id] = {
                "review_observation_id": observation_id,
                "archive_id": candidate["archive_id"],
                "cik": candidate["cik"],
                "adsh": candidate["adsh"],
                "economic_facility_id": candidate["economic_facility_id"],
                "selection_reason": reason,
            }
        output.append({field: row[field] for field in OUTPUT_FIELDS})
    return output, {
        "schema_version": "phase_c_structural_evidence_key_v1",
        "phase_b_sample_freeze_commit": PHASE_B_COMMIT,
        "target_current_evidence_mapping": private_mappings,
        "mapping_reason_counts": dict(sorted(mapping_reasons.items())),
    }


def id_hash(values: list[str]) -> str:
    return hashlib.sha256(("\n".join(values) + "\n").encode("utf-8")).hexdigest()


def validate(rows: list[dict[str, str]], included: list[dict[str, str]]) -> None:
    if len(rows) != EXPECTED_ROWS:
        raise RuntimeError(f"Expected {EXPECTED_ROWS} structural rows, found {len(rows)}")
    row_ids = [row["review_observation_id"] for row in rows]
    frozen_ids = [row["review_observation_id"] for row in included]
    if row_ids != frozen_ids or len(row_ids) != len(set(row_ids)):
        raise RuntimeError("Structural packet IDs/order do not equal frozen sample")
    if len({row["source_event_cluster_id"] for row in rows}) != EXPECTED_CLUSTERS:
        raise RuntimeError("Structural packet cluster count changed")
    forbidden = [
        field for field in OUTPUT_FIELDS
        if any(token in field.casefold() for token in FORBIDDEN_HEADER_TOKENS)
    ]
    if forbidden:
        raise RuntimeError(f"Prohibited structural-packet fields: {forbidden}")
    if any(row[field] for row in rows for field in REVIEW_FIELDS):
        raise RuntimeError("Structural reviewer fields must be blank")


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--included-sample",
        type=Path,
        default=Path("data/day4/confirmatory_included_sample.csv"),
    )
    parser.add_argument(
        "--sanitized-phase-a-packet",
        type=Path,
        default=Path("data/day4/confirmatory_event_review_blind_v2.csv"),
    )
    parser.add_argument(
        "--facilities",
        type=Path,
        default=Path(
            "/private/tmp/finance-day3-sec-cache/bdc_facilities_agg_lineage_v2.csv"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/day4/target_current_structural_review_blind.csv"),
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path("data/day4/target_current_structural_review_meta.json"),
    )
    parser.add_argument(
        "--private-evidence-key",
        type=Path,
        default=Path("private/day4/structural_review_evidence_key.json"),
    )
    args = parser.parse_args()

    assert_sha(args.included_sample, INCLUDED_SAMPLE_SHA256)
    assert_sha(args.sanitized_phase_a_packet, SANITIZED_PACKET_SHA256)
    assert_sha(args.facilities, FACILITIES_SHA256)
    included = read_csv(args.included_sample)
    packet = read_csv(args.sanitized_phase_a_packet)
    packet_by_id = {row["review_observation_id"]: row for row in packet}
    frozen_ids = [row["review_observation_id"] for row in included]
    if any(observation_id not in packet_by_id for observation_id in frozen_ids):
        raise RuntimeError("Frozen ID is missing from sanitized Phase A packet")
    wanted_keys = {
        (row["target_ticker"], row["period_end"], row["normalized_borrower"])
        for row in included
    }
    current_by_key = projected_current_facilities(args.facilities, wanted_keys)
    rows, private_key = build_rows(included, packet_by_id, current_by_key)
    validate(rows, included)
    write_csv(args.output, rows)
    write_json(args.private_evidence_key, private_key)
    private_key_sha = sha256_file(args.private_evidence_key)
    packet_sha = sha256_file(args.output)
    meta = {
        "status": "phase_c_structural_review_packet_unlabeled",
        "phase_b_sample_freeze_commit": PHASE_B_COMMIT,
        "structural_packet_sha256": packet_sha,
        "review_observations": len(rows),
        "source_event_clusters": len({
            row["source_event_cluster_id"] for row in rows
        }),
        "ordered_observation_id_sha256": id_hash([
            row["review_observation_id"] for row in rows
        ]),
        "ordered_frozen_observation_id_sha256": id_hash(frozen_ids),
        "exact_frozen_id_order_match": True,
        "structurally_mapped_rows": sum(
            bool(row["target_current_evidence_id"]) for row in rows
        ),
        "structurally_unmapped_rows_retained": sum(
            not row["target_current_evidence_id"] for row in rows
        ),
        "private_evidence_key_sha256": private_key_sha,
        "private_evidence_key_tracked": False,
        "facility_reader_projection": list(FACILITY_PROJECTION),
        "numeric_valuation_columns_projected_or_used": False,
        "principal_cost_fair_value_or_ratio_in_packet": False,
        "source_movement_or_prediction_in_packet": False,
        "phase_a_labels_notes_or_inclusion_in_packet": False,
        "navigable_urls_accessions_or_raw_provenance_in_packet": False,
        "review_fields_blank": True,
        "numeric_reveal_authorized": False,
        "numeric_evaluation_run": False,
        "results_tag_authorized": False,
        "output_schema": list(OUTPUT_FIELDS),
        "input_sha256": {
            "included_sample": sha256_file(args.included_sample),
            "sanitized_phase_a_packet": sha256_file(args.sanitized_phase_a_packet),
            "economic_facility_v2_lineage": sha256_file(args.facilities),
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

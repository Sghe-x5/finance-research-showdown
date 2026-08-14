#!/usr/bin/env python3
"""Build the Day 4 outcome-blind human event-review packet.

The builder selects previously identified source movements, then joins only
source-current, source-prior, and target-prior economic facilities. It never
loads a target-current facility or any target outcome.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ELIGIBLE_SHA256 = "81c2cde597fd1b64499787da2ffa719682a27bd88f27d097e5eb459f410ddc24"
FACILITIES_SHA256 = "60aee6b26872b65a0845a58db286e3409518498532d2eb69d0ffc7c1d356bbec"
REPORTING_SHA256 = "11bfabd0faf0507c47cee950d82dc89f77e6d2b827bba44b666df6f42005ca8b"
MANAGER_MAP_SHA256 = "e3850b8721d192cd93f758b79e4824bb7993fc74ac8f9b56da36d7e82934bdb6"
MOVEMENT_THRESHOLD = 0.005
DEVELOPMENT_PERIOD = "2025Q3"
EXPECTED_OBSERVATIONS = 40
EXPECTED_CLUSTERS = 37
EXPECTED_FACILITY_IDS = 96

REVIEW_FIELDS = (
    "source_temporal_same_facility",
    "source_to_target_prior_same_facility",
    "source_aggregation_valid",
    "target_prior_aggregation_valid",
    "include_for_confirmatory_test",
    "review_notes",
)

ATTRIBUTES = (
    "facility_type",
    "lien",
    "currency",
    "reference_rate",
    "spread",
    "maturity",
    "funded_status",
    "acquisition_date",
)

SIDE_FIELDS = (
    "raw_identifier",
    *ATTRIBUTES,
    "constituent_raw_identifiers_json",
    "aggregation_lot_count",
    "accepted_timestamp_utc",
    "filing_evidence_url",
    "raw_provenance_json",
)

OUTPUT_FIELDS = (
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
    *(f"{side}_{field}" for side in ("source_current", "source_prior", "target_prior") for field in SIDE_FIELDS),
    "source_results_public_timestamp_utc",
    "source_mark_public_timestamp_utc",
    "source_information_timestamp_utc",
    "source_mark_public_evidence",
    "source_results_evidence_url",
    "source_results_verification_evidence",
    "source_prior_public_timestamp_utc",
    "source_prior_reporting_evidence_url",
    "target_prior_public_timestamp_utc",
    "target_prior_reporting_evidence_url",
    "target_cutoff_timestamp_utc",
    "target_cutoff_evidence_url",
    "target_cutoff_verification_evidence",
    *REVIEW_FIELDS,
)

PROHIBITED_OUTPUT_FIELDS = {
    "source_current_mark",
    "source_prior_mark",
    "source_mark_delta",
    "source_delta_mark",
    "source_delta_pp",
    "principal",
    "cost",
    "fair_value",
    "target_current_identifier",
    "target_current_facility",
    "target_current_mark",
    "model_prediction",
    "target_outcome",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(prefix: str, *parts: str, length: int = 24) -> str:
    material = "\x1f".join(parts).encode("utf-8")
    return prefix + hashlib.sha256(material).hexdigest()[:length]


def id_set_sha256(values) -> str:
    canonical = json.dumps(sorted(set(values)), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


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


def assert_sha(path: Path, expected: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"Input SHA-256 mismatch for {path}: {actual} != {expected}")


def select_movements(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    selected = []
    for row in rows:
        if row["target_current_outcome_used_for_eligibility"] != "False":
            raise RuntimeError("Eligibility input reports target-current outcome use")
        if row["outcomes_revealed"] != "False":
            raise RuntimeError("Eligibility input reports revealed outcomes")
        if row["report_period_label"] == DEVELOPMENT_PERIOD:
            continue
        if row["development_borrower_excluded"] != "False":
            continue
        if row["movement_eligible"] != "True":
            continue
        delta = float(row["source_delta_mark"])
        if abs(delta) < MOVEMENT_THRESHOLD:
            raise RuntimeError("Movement flag conflicts with the locked 0.005 threshold")
        selected.append(row)
    if len(selected) != EXPECTED_OBSERVATIONS:
        raise RuntimeError(f"Expected {EXPECTED_OBSERVATIONS} movement observations, found {len(selected)}")
    return selected


def load_selected_facilities(path: Path, wanted: set[str]) -> dict[str, dict[str, str]]:
    found = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            facility_id = row["economic_facility_id"]
            if facility_id in wanted:
                if facility_id in found:
                    raise RuntimeError(f"Duplicate economic facility ID: {facility_id}")
                found[facility_id] = row
    missing = wanted - set(found)
    if missing:
        raise RuntimeError(f"Missing {len(missing)} point-in-time economic facilities")
    return found


def filing_url(facility: dict[str, str]) -> str:
    cik = str(int(facility["cik"]))
    accession = facility["adsh"].replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/"


def constituent_identifiers(identifier: str) -> str:
    values = sorted({value.strip() for value in identifier.split(" | ") if value.strip()})
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"))


def side_values(prefix: str, facility: dict[str, str]) -> dict[str, str]:
    values = {
        f"{prefix}_raw_identifier": facility["investment_identifier"],
        f"{prefix}_constituent_raw_identifiers_json": constituent_identifiers(
            facility["investment_identifier"]
        ),
        f"{prefix}_aggregation_lot_count": facility["lot_count"],
        f"{prefix}_accepted_timestamp_utc": utc_iso(facility["accepted"]),
        f"{prefix}_filing_evidence_url": filing_url(facility),
        f"{prefix}_raw_provenance_json": facility["raw_provenance_json"],
    }
    for field in ATTRIBUTES:
        values[f"{prefix}_{field}"] = facility[field]
    return values


def reporting_index(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    index = {}
    for row in rows:
        key = (row["ticker"], row["report_period_end"])
        if key in index:
            raise RuntimeError(f"Duplicate reporting-order row: {key}")
        index[key] = row
    return index


def evidence_url(row: dict[str, str]) -> str:
    return row.get("exhibit_url") or row.get("periodic_filing_url") or ""


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def utc_iso(value: str) -> str:
    return parse_timestamp(value).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def later_timestamp(left: str, right: str) -> str:
    selected = left if parse_timestamp(left) >= parse_timestamp(right) else right
    return utc_iso(selected)


def build_rows(
    selected: list[dict[str, str]],
    facilities: dict[str, dict[str, str]],
    reporting: dict[tuple[str, str], dict[str, str]],
    managers: dict[str, str],
) -> list[dict[str, str]]:
    output = []
    for eligible in selected:
        current = facilities[eligible["source_facility_id"]]
        source_prior = facilities[eligible["source_prior_facility_id"]]
        target_prior = facilities[eligible["target_prior_facility_id"]]
        borrower = eligible["borrower_norm"]
        if {current["borrower_norm"], source_prior["borrower_norm"], target_prior["borrower_norm"]} != {borrower}:
            raise RuntimeError("A review row escaped exact normalized borrower blocking")
        if current["aggregation_rule_version"] != "economic_facility_v2":
            raise RuntimeError("Source current facility is not economic_facility_v2")
        if source_prior["aggregation_rule_version"] != "economic_facility_v2":
            raise RuntimeError("Source prior facility is not economic_facility_v2")
        if target_prior["aggregation_rule_version"] != "economic_facility_v2":
            raise RuntimeError("Target prior facility is not economic_facility_v2")

        source_manager = managers[eligible["source_ticker"]]
        target_manager = managers[eligible["target_ticker"]]
        relationship = "same_manager" if source_manager == target_manager else "cross_manager"
        if relationship != "cross_manager":
            raise RuntimeError("Same-manager observation entered the confirmatory packet")

        period = eligible["report_period_end"]
        source_report = reporting[(eligible["source_ticker"], period)]
        target_report = reporting[(eligible["target_ticker"], period)]
        source_prior_report = reporting[(eligible["source_ticker"], source_prior["period_end"])]
        target_prior_report = reporting[(eligible["target_ticker"], target_prior["period_end"])]
        cluster_id = stable_id(
            "D4C_", period, eligible["source_ticker"], eligible["source_facility_id"]
        )
        review_id = stable_id("D4R_", eligible["observation_id"])
        row = {
            "review_observation_id": review_id,
            "source_event_cluster_id": cluster_id,
            "period_end": period,
            "report_period_label": eligible["report_period_label"],
            "normalized_borrower": borrower,
            "source_ticker": eligible["source_ticker"],
            "target_ticker": eligible["target_ticker"],
            "source_manager": source_manager,
            "target_manager": target_manager,
            "manager_relationship": relationship,
            **side_values("source_current", current),
            **side_values("source_prior", source_prior),
            **side_values("target_prior", target_prior),
            "source_results_public_timestamp_utc": eligible["source_results_timestamp_utc"],
            "source_mark_public_timestamp_utc": eligible["source_mark_public_timestamp_utc"],
            "source_information_timestamp_utc": eligible["source_information_timestamp_utc"],
            "source_mark_public_evidence": eligible["source_mark_public_evidence"],
            "source_results_evidence_url": evidence_url(source_report),
            "source_results_verification_evidence": source_report["verification_evidence"],
            "source_prior_public_timestamp_utc": later_timestamp(
                source_prior["accepted"], source_prior_report["acceptance_timestamp_utc"]
            ),
            "source_prior_reporting_evidence_url": evidence_url(source_prior_report),
            "target_prior_public_timestamp_utc": eligible["target_prior_public_timestamp_utc"],
            "target_prior_reporting_evidence_url": evidence_url(target_prior_report),
            "target_cutoff_timestamp_utc": eligible["target_cutoff_timestamp_utc"],
            "target_cutoff_evidence_url": evidence_url(target_report),
            "target_cutoff_verification_evidence": target_report["verification_evidence"],
            **{field: "" for field in REVIEW_FIELDS},
        }
        output.append(row)
    output.sort(key=lambda row: row["review_observation_id"])
    if len({row["review_observation_id"] for row in output}) != len(output):
        raise RuntimeError("Duplicate review observation ID")
    if len({row["source_event_cluster_id"] for row in output}) != EXPECTED_CLUSTERS:
        raise RuntimeError("Unexpected independent source-event cluster count")
    return output


def validate_output(rows: list[dict[str, str]]) -> None:
    headers = set(OUTPUT_FIELDS)
    if headers & PROHIBITED_OUTPUT_FIELDS:
        raise RuntimeError(f"Prohibited output fields present: {headers & PROHIBITED_OUTPUT_FIELDS}")
    if any("target_current" in field for field in headers):
        raise RuntimeError("Target-current field present in review packet")
    if any(row["manager_relationship"] != "cross_manager" for row in rows):
        raise RuntimeError("Non-cross-manager row present")
    if any(row["report_period_label"] == DEVELOPMENT_PERIOD for row in rows):
        raise RuntimeError("Development period present")
    if any(row[field] for row in rows for field in REVIEW_FIELDS):
        raise RuntimeError("Human review fields must be blank")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--eligible", type=Path, default=Path("data/day3/eligible_prefreeze_extended.csv")
    )
    parser.add_argument(
        "--facilities",
        type=Path,
        default=Path("/private/tmp/finance-day3-sec-cache/bdc_facilities_agg_lineage_v2.csv"),
    )
    parser.add_argument(
        "--reporting", type=Path, default=Path("data/day3/reporting_order_extended.csv")
    )
    parser.add_argument(
        "--manager-map", type=Path, default=Path("data/day3/bdc_manager_map.csv")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/day4/confirmatory_event_review_blind.csv")
    )
    parser.add_argument(
        "--metadata", type=Path, default=Path("data/day4/confirmatory_event_review_meta.json")
    )
    args = parser.parse_args()

    for path, expected in (
        (args.eligible, ELIGIBLE_SHA256),
        (args.facilities, FACILITIES_SHA256),
        (args.reporting, REPORTING_SHA256),
        (args.manager_map, MANAGER_MAP_SHA256),
    ):
        assert_sha(path, expected)

    eligible_rows = read_csv(args.eligible)
    selected = select_movements(eligible_rows)
    wanted = {
        row[field]
        for row in selected
        for field in ("source_facility_id", "source_prior_facility_id", "target_prior_facility_id")
    }
    if len(wanted) != EXPECTED_FACILITY_IDS:
        raise RuntimeError(f"Expected {EXPECTED_FACILITY_IDS} facility IDs, found {len(wanted)}")
    facilities = load_selected_facilities(args.facilities, wanted)
    reporting = reporting_index(read_csv(args.reporting))
    managers = {
        row["ticker"]: row["canonical_manager"] for row in read_csv(args.manager_map)
    }
    rows = build_rows(selected, facilities, reporting, managers)
    validate_output(rows)
    write_csv(args.output, rows)

    cluster_sizes = Counter(row["source_event_cluster_id"] for row in rows)
    per_period = {
        period: {
            "observations": sum(row["report_period_label"] == period for row in rows),
            "independent_source_event_clusters": len({
                row["source_event_cluster_id"]
                for row in rows
                if row["report_period_label"] == period
            }),
        }
        for period in sorted({row["report_period_label"] for row in rows})
    }
    metadata = {
        "status": "outcome_blind_human_review_packet_not_labeled",
        "review_packet_sha256": sha256_file(args.output),
        "review_packet_rows": len(rows),
        "review_observation_ids_sha256": id_set_sha256(
            row["review_observation_id"] for row in rows
        ),
        "independent_source_event_clusters": len(cluster_sizes),
        "source_event_cluster_ids_sha256": id_set_sha256(cluster_sizes),
        "cluster_size_distribution": dict(sorted(Counter(cluster_sizes.values()).items())),
        "periods": per_period,
        "selection": {
            "periods": "2024Q1-2025Q2",
            "development_period_excluded": DEVELOPMENT_PERIOD,
            "movement_definition": "abs(source_current_mark - source_prior_mark) >= 0.005",
            "movement_threshold": MOVEMENT_THRESHOLD,
            "exact_normalized_borrower_only": True,
            "borrower_aliases_used": False,
            "same_manager_observations_used": False,
            "economic_facility_rule": "economic_facility_v2",
            "all_observations_cross_manager": True,
            "all_11_seen_development_borrowers_excluded_upstream": True,
        },
        "input_sha256": {
            "eligible_prefreeze_extended": sha256_file(args.eligible),
            "economic_facility_v2_lineage": sha256_file(args.facilities),
            "reporting_order_extended": sha256_file(args.reporting),
            "canonical_manager_map": sha256_file(args.manager_map),
        },
        "output_schema": list(OUTPUT_FIELDS),
        "human_review_fields_blank": True,
        "inclusion_rule": (
            "include_for_confirmatory_test=yes only when the four measurement checks are all yes"
        ),
        "target_current_fields_present": False,
        "target_outcomes_opened": False,
        "source_or_target_numeric_marks_in_packet": False,
        "principal_cost_or_fair_value_in_packet": False,
        "model_prediction_in_packet": False,
        "freeze_authorized": False,
        "reveal_authorized": False,
        "results_tag_authorized": False,
    }
    write_json(args.metadata, metadata)
    print(json.dumps({
        "packet": str(args.output),
        "sha256": metadata["review_packet_sha256"],
        "observations": len(rows),
        "clusters": len(cluster_sizes),
        "periods": per_period,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

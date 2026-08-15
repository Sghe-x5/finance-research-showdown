#!/usr/bin/env python3
"""Build the outcome-blind Day 5 event-review packet.

The builder joins only source-current, source-prior, and target-prior
economic-facility structure. It never looks up a target-current facility and
never reads or exports valuation fields.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import json
import secrets
from pathlib import Path


EXPECTED_STRICT = (34, 34, 19)
EXPECTED_SUPPORTING = (75, 75, 39)

REVIEW_FIELDS = (
    "source_temporal_same_facility",
    "source_to_target_prior_same_facility",
    "source_aggregation_valid",
    "target_prior_aggregation_valid",
    "include_for_replication",
    "review_notes",
)

STRUCTURAL_FIELDS = (
    "raw_identifier",
    "facility_type",
    "lien",
    "currency",
    "reference_rate",
    "spread",
    "maturity",
    "funded_status",
    "acquisition_date",
    "constituent_descriptions_json",
    "aggregation_lot_count",
    "accepted_timestamp_utc",
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
    *(f"{side}_{field}" for side in ("source_current", "source_prior", "target_prior") for field in STRUCTURAL_FIELDS),
    "source_current_evidence_id",
    "source_prior_evidence_id",
    "target_prior_evidence_id",
    "source_mark_public_timestamp_utc",
    "target_cutoff_timestamp_utc",
    "reporting_window_days",
    "source_timing_evidence_id",
    "source_timing_evidence_statement",
    "target_cutoff_evidence_id",
    "target_cutoff_evidence_statement",
    *REVIEW_FIELDS,
)

FORBIDDEN_OUTPUT_TOKENS = (
    "target_current",
    "principal",
    "cost",
    "fair_value",
    "fv_to_principal",
    "mark_fv",
    "source_current_mark",
    "source_prior_mark",
    "source_delta",
    "prediction",
    "error",
    "return",
    "url",
    "accession",
    "provenance",
    "archive",
    "strict_new_borrower",
    "new_fund_universe",
    "layer",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_set_sha256(values) -> str:
    payload = json.dumps(sorted(set(values)), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def ordered_sha256(values) -> str:
    payload = json.dumps(list(values), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def stable_id(prefix: str, *parts: str, length: int = 24) -> str:
    material = "\x1f".join(parts).encode("utf-8")
    return prefix + hashlib.sha256(material).hexdigest()[:length]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def flag(row: dict[str, str], field: str) -> bool:
    return row[field].strip().lower() == "true"


def describe(rows: list[dict[str, str]]) -> tuple[int, int, int]:
    return (
        len(rows),
        len({row["source_event_cluster_id"] for row in rows}),
        len({row["normalized_borrower"] for row in rows}),
    )


def mechanical_inclusion(labels) -> str:
    """Apply the locked event-review inclusion rule to four labels."""
    values = list(labels)
    if len(values) != 4 or any(value not in {"yes", "no", "uncertain"} for value in values):
        raise ValueError("Exactly four yes/no/uncertain labels are required")
    if "no" in values:
        return "no"
    if "uncertain" in values:
        return "uncertain"
    return "yes"


def facility_projection(row: dict[str, str]) -> dict[str, str]:
    """Project only non-valuation structure from an aggregate facility row."""
    identifiers = sorted({
        value.strip()
        for value in row["investment_identifier"].split(" | ")
        if value.strip()
    })
    return {
        "economic_facility_id": row["economic_facility_id"],
        "archive_id": row["archive_id"],
        "adsh": row["adsh"],
        "cik": row["cik"],
        "ticker": row["ticker"],
        "accepted": row["accepted"],
        "period_end": row["period_end"],
        "borrower_norm": row["borrower_norm"],
        "raw_identifier": row["investment_identifier"],
        "facility_type": row["facility_type"],
        "lien": row["lien"],
        "currency": row["currency"],
        "reference_rate": row["reference_rate"],
        "spread": row["spread"],
        "maturity": row["maturity"],
        "funded_status": row["funded_status"],
        "acquisition_date": row["acquisition_date"],
        "constituent_descriptions_json": json.dumps(
            identifiers, ensure_ascii=False, separators=(",", ":")
        ),
        "aggregation_lot_count": row["lot_count"],
        "aggregation_rule_version": row["aggregation_rule_version"],
        "raw_provenance_json": row["raw_provenance_json"],
    }


def load_facilities(paths: list[Path], wanted: set[str]) -> dict[str, dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    for path in paths:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            for raw in csv.DictReader(handle):
                facility_id = raw["economic_facility_id"]
                if facility_id not in wanted:
                    continue
                projected = facility_projection(raw)
                previous = found.setdefault(facility_id, projected)
                if previous != projected:
                    raise RuntimeError(f"Conflicting economic facility ID: {facility_id}")
    missing = wanted - set(found)
    if missing:
        raise RuntimeError(f"Missing {len(missing)} facilities: {sorted(missing)[:5]}")
    return found


def load_or_create_secret(private_path: Path) -> str:
    if not private_path.exists():
        return secrets.token_hex(32)
    payload = json.loads(private_path.read_text(encoding="utf-8"))
    secret = payload.get("hmac_secret_hex", "")
    if len(secret) != 64:
        raise RuntimeError("Existing private Day 5 key has an invalid HMAC secret")
    return secret


def evidence_id(secret: str, scope: str, payload: dict) -> str:
    message = json.dumps(
        {"scope": scope, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hmac.new(bytes.fromhex(secret), message, hashlib.sha256).hexdigest()
    return "EVID_" + digest[:28]


def side_public(prefix: str, facility: dict[str, str]) -> dict[str, str]:
    return {
        f"{prefix}_{field}": facility[field]
        for field in STRUCTURAL_FIELDS
        if field != "accepted_timestamp_utc"
    } | {f"{prefix}_accepted_timestamp_utc": facility["accepted"]}


def build(
    candidates: list[dict[str, str]],
    facilities: dict[str, dict[str, str]],
    secret: str,
) -> tuple[list[dict[str, str]], dict]:
    strict = [row for row in candidates if flag(row, "strict_new_borrower_universe")]
    supporting = [row for row in candidates if flag(row, "new_fund_universe")]
    if describe(strict) != EXPECTED_STRICT:
        raise RuntimeError(f"STRICT candidate counts changed: {describe(strict)}")
    if describe(supporting) != EXPECTED_SUPPORTING:
        raise RuntimeError(f"SUPPORTING candidate counts changed: {describe(supporting)}")

    strict_ids = {row["candidate_observation_id"] for row in strict}
    supporting_ids = {row["candidate_observation_id"] for row in supporting}
    strict_subset = strict_ids <= supporting_ids
    review_candidates = supporting if strict_subset else [
        row for row in candidates
        if row["candidate_observation_id"] in strict_ids | supporting_ids
    ]
    review_candidates = sorted(
        review_candidates,
        key=lambda row: (
            row["report_period_label"], row["normalized_borrower"],
            row["source_fund_id"], row["target_fund_id"],
            row["candidate_observation_id"],
        ),
    )

    public_rows = []
    private_rows = {}
    opaque_evidence = {}
    review_cluster_by_candidate_cluster: dict[str, str] = {}
    for candidate in review_candidates:
        review_id = stable_id("D5EV_", "day5-event-review-v1", candidate["candidate_observation_id"])
        review_cluster_id = review_cluster_by_candidate_cluster.setdefault(
            candidate["source_event_cluster_id"],
            stable_id("D5EC_", "day5-event-cluster-v1", candidate["source_event_cluster_id"]),
        )
        sides = {
            "source_current": facilities[candidate["source_facility_id"]],
            "source_prior": facilities[candidate["source_prior_facility_id"]],
            "target_prior": facilities[candidate["target_prior_facility_id"]],
        }
        if {side["borrower_norm"] for side in sides.values()} != {candidate["normalized_borrower"]}:
            raise RuntimeError("Candidate escaped exact normalized-borrower blocking")
        if any(side["aggregation_rule_version"] != "economic_facility_v2" for side in sides.values()):
            raise RuntimeError("Candidate is not based on economic_facility_v2")

        side_ids = {}
        for side_name, facility in sides.items():
            underlying = {
                "economic_facility_id": facility["economic_facility_id"],
                "archive_id": facility["archive_id"],
                "adsh": facility["adsh"],
                "cik": facility["cik"],
                "accepted": facility["accepted"],
                "raw_provenance_json": facility["raw_provenance_json"],
            }
            opaque = evidence_id(secret, side_name, underlying)
            side_ids[side_name] = opaque
            opaque_evidence[opaque] = {"scope": side_name, "underlying": underlying}

        timing_underlying = {
            "source_mark_public_timestamp_utc": candidate["source_mark_public_timestamp_utc"],
            "target_cutoff_timestamp_utc": candidate["target_cutoff_timestamp_utc"],
            "target_cutoff_basis": candidate["target_cutoff_basis"],
            "source_facility_id": candidate["source_facility_id"],
            "target_cik": candidate["target_cik"],
        }
        source_timing_id = evidence_id(secret, "source_timing", timing_underlying)
        target_cutoff_id = evidence_id(secret, "target_cutoff", timing_underlying)
        opaque_evidence[source_timing_id] = {"scope": "source_timing", "underlying": timing_underlying}
        opaque_evidence[target_cutoff_id] = {"scope": "target_cutoff", "underlying": timing_underlying}

        row = {
            "review_observation_id": review_id,
            "source_event_cluster_id": review_cluster_id,
            "period_end": candidate["period_end"],
            "report_period_label": candidate["report_period_label"],
            "normalized_borrower": candidate["normalized_borrower"],
            "source_ticker": candidate["source_fund_id"],
            "target_ticker": candidate["target_fund_id"],
            "source_manager": candidate["source_manager_family"],
            "target_manager": candidate["target_manager_family"],
            "manager_relationship": candidate["manager_relationship"],
            "source_current_evidence_id": side_ids["source_current"],
            "source_prior_evidence_id": side_ids["source_prior"],
            "target_prior_evidence_id": side_ids["target_prior"],
            "source_mark_public_timestamp_utc": candidate["source_mark_public_timestamp_utc"],
            "target_cutoff_timestamp_utc": candidate["target_cutoff_timestamp_utc"],
            "reporting_window_days": candidate["reporting_window_days"],
            "source_timing_evidence_id": source_timing_id,
            "source_timing_evidence_statement": (
                "The source facility mark-public timestamp was verified in the locked "
                "outcome-blind feasibility inputs."
            ),
            "target_cutoff_evidence_id": target_cutoff_id,
            "target_cutoff_evidence_statement": (
                "The target cutoff is the earliest verified public results/NAV disclosure "
                "in the locked outcome-blind feasibility inputs."
            ),
            **{field: "" for field in REVIEW_FIELDS},
        }
        for side_name, facility in sides.items():
            row.update(side_public(side_name, facility))
        public_rows.append(row)
        private_rows[review_id] = {
            "candidate_observation_id": candidate["candidate_observation_id"],
            "candidate_source_event_cluster_id": candidate["source_event_cluster_id"],
            "review_source_event_cluster_id": review_cluster_id,
            "strict_new_borrower": candidate["candidate_observation_id"] in strict_ids,
            "supporting_new_fund": candidate["candidate_observation_id"] in supporting_ids,
            "overlap_day4_borrower": candidate["overlap_day4_borrower"],
            "overlap_development_borrower": candidate["overlap_development_borrower"],
            "source_facility_id": candidate["source_facility_id"],
            "source_prior_facility_id": candidate["source_prior_facility_id"],
            "target_prior_facility_id": candidate["target_prior_facility_id"],
        }

    if len({row["review_observation_id"] for row in public_rows}) != len(public_rows):
        raise RuntimeError("Duplicate opaque review observation IDs")
    if any(token in field.lower() for field in OUTPUT_FIELDS for token in FORBIDDEN_OUTPUT_TOKENS):
        raise RuntimeError("Blind output header contains a prohibited field")
    return public_rows, {
        "hmac_secret_hex": secret,
        "review_rows": private_rows,
        "evidence": opaque_evidence,
        "strict_is_subset_of_supporting": strict_subset,
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, default=Path("data/day5/replication_universe_candidates_v2.csv"))
    parser.add_argument("--historical-facilities", type=Path, default=Path("/private/tmp/finance-day3-sec-cache/bdc_facilities_all_agg.csv"))
    parser.add_argument("--new-facilities", type=Path, default=Path("/private/tmp/finance-day5-sec-cache/bdc_facilities_2026_new_agg.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/day5/day5_event_review_blind.csv"))
    parser.add_argument("--meta", type=Path, default=Path("data/day5/day5_event_review_blind_meta.json"))
    parser.add_argument("--private-key", type=Path, default=Path("private/day5/day5_event_review_key.json"))
    parser.add_argument("--preregistration", type=Path, default=Path("docs/research/DAY5_REPLICATION_PREREGISTRATION_DRAFT.md"))
    parser.add_argument("--evaluator", type=Path, default=Path("scripts/day5/evaluate_day5_replication.py"))
    args = parser.parse_args()

    candidates = read_csv(args.candidates)
    strict = [row for row in candidates if flag(row, "strict_new_borrower_universe")]
    supporting = [row for row in candidates if flag(row, "new_fund_universe")]
    wanted = {
        row[field]
        for row in supporting
        for field in ("source_facility_id", "source_prior_facility_id", "target_prior_facility_id")
    }
    facilities = load_facilities([args.historical_facilities, args.new_facilities], wanted)
    secret = load_or_create_secret(args.private_key)
    rows, private_payload = build(candidates, facilities, secret)
    write_csv(args.output, rows)
    write_json(args.private_key, private_payload)

    strict_ids = [row["candidate_observation_id"] for row in strict]
    supporting_ids = [row["candidate_observation_id"] for row in supporting]
    strict_clusters = [row["source_event_cluster_id"] for row in strict]
    supporting_clusters = [row["source_event_cluster_id"] for row in supporting]
    strict_borrowers = [row["normalized_borrower"] for row in strict]
    supporting_borrowers = [row["normalized_borrower"] for row in supporting]
    meta = {
        "status": "outcome_blind_candidate_review_preparation_not_sample_freeze",
        "strict_is_subset_of_supporting": set(strict_ids) <= set(supporting_ids),
        "review_universe_rule": "supporting_candidate_rows" if set(strict_ids) <= set(supporting_ids) else "union_of_strict_and_supporting",
        "blind_packet_rows": len(rows),
        "blind_packet_source_event_clusters": len({row["source_event_cluster_id"] for row in rows}),
        "strict_candidate_counts": {"observations": len(strict), "source_event_clusters": len(set(strict_clusters)), "borrowers": len(set(strict_borrowers))},
        "supporting_candidate_counts": {"observations": len(supporting), "source_event_clusters": len(set(supporting_clusters)), "borrowers": len(set(supporting_borrowers))},
        "sha256": {
            "candidate_file": sha256_file(args.candidates),
            "blind_review_packet": sha256_file(args.output),
            "strict_candidate_observation_id_set": canonical_set_sha256(strict_ids),
            "supporting_candidate_observation_id_set": canonical_set_sha256(supporting_ids),
            "ordered_review_observation_ids": ordered_sha256(row["review_observation_id"] for row in rows),
            "strict_source_event_cluster_set": canonical_set_sha256(strict_clusters),
            "supporting_source_event_cluster_set": canonical_set_sha256(supporting_clusters),
            "strict_borrower_set": canonical_set_sha256(strict_borrowers),
            "supporting_borrower_set": canonical_set_sha256(supporting_borrowers),
            "preregistration_draft": sha256_file(args.preregistration),
            "evaluator": sha256_file(args.evaluator),
            "private_review_and_evidence_key": sha256_file(args.private_key),
        },
        "private_key_path": str(args.private_key),
        "private_key_gitignored": True,
        "reviewer_packet_exposes_layer_membership": False,
        "human_review_may_remove_but_never_add_replace_or_move_rows": True,
        "prohibitions": {
            "target_current_structure_opened": False,
            "target_current_numeric_marks_opened": False,
            "predictions_errors_or_statistics_calculated": False,
            "final_sample_frozen": False,
            "result_tag_created": False,
        },
    }
    write_json(args.meta, meta)


if __name__ == "__main__":
    main()

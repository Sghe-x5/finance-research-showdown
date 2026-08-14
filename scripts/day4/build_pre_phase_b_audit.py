#!/usr/bin/env python3
"""Build outcome-blind dependence and duplicate-vote audits before Phase B.

The script combines final Phase A decisions from the independent-review partial
consensus and the separate adjudication file. It reads only the sanitized event
packet and pre-reveal economic facility IDs. It never opens target-current
structure, numeric outcomes, predictions, or errors.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


MEASUREMENT_CHECKS = (
    "source_temporal_same_facility",
    "source_to_target_prior_same_facility",
    "source_aggregation_valid",
    "target_prior_aggregation_valid",
)
INCLUDE_FIELD = "include_for_confirmatory_test"
DISTRIBUTION_FIELDS = (
    "normalized_borrower",
    "included_source_event_cluster_count",
    "included_observation_count",
    "report_period_count",
    "source_ticker_count",
    "target_ticker_count",
)
INCLUDED_SAMPLE_FIELDS = (
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
DUPLICATE_IDENTITY_FIELDS = (
    "report_period",
    "normalized_borrower",
    "source_ticker",
    "target_ticker",
    "source_prior_economic_facility_id",
    "target_prior_economic_facility_id",
)
PHASE_A_REVIEW_COLUMNS = {
    *MEASUREMENT_CHECKS,
    INCLUDE_FIELD,
    "review_notes",
    *(f"consensus_{field}" for field in (*MEASUREMENT_CHECKS, INCLUDE_FIELD)),
    *(f"adjudicated_{field}" for field in (*MEASUREMENT_CHECKS, INCLUDE_FIELD)),
}
PHASE_C_NUMERIC_FORBIDDEN_TOKENS = (
    "mark",
    "principal",
    "cost",
    "fair_value",
    "fv_par",
    "prediction",
    "error",
    "outcome",
    "source_delta",
    "movement_size",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def stable_review_id(observation_id: str) -> str:
    return "D4R_" + hashlib.sha256(observation_id.encode("utf-8")).hexdigest()[:24]


def expected_inclusion(labels: dict[str, str]) -> str:
    checks = [labels[field] for field in MEASUREMENT_CHECKS]
    if any(label not in {"yes", "no", "uncertain"} for label in checks):
        raise ValueError("Final measurement checks contain an invalid label")
    if "no" in checks:
        return "no"
    if "uncertain" in checks:
        return "uncertain"
    return "yes"


def derive_final_consensus(
    partial_rows: list[dict[str, str]],
    adjudication_rows: list[dict[str, str]],
) -> dict[str, dict[str, str]]:
    adjudication = {
        row["review_observation_id"]: row for row in adjudication_rows
    }
    if len(adjudication) != len(adjudication_rows):
        raise ValueError("Adjudication observation IDs are duplicated")

    final = {}
    adjudication_needed = set()
    for row in partial_rows:
        observation_id = row["review_observation_id"]
        if not observation_id or observation_id in final:
            raise ValueError("Partial-consensus observation IDs are blank or duplicated")
        partial_labels = {
            field: row.get(f"consensus_{field}", "").strip()
            for field in (*MEASUREMENT_CHECKS, INCLUDE_FIELD)
        }
        if all(partial_labels.values()):
            labels = partial_labels
        else:
            adjudication_needed.add(observation_id)
            if observation_id not in adjudication:
                raise ValueError(f"Missing adjudication for {observation_id}")
            labels = {
                field: adjudication[observation_id].get(
                    f"adjudicated_{field}", ""
                ).strip()
                for field in (*MEASUREMENT_CHECKS, INCLUDE_FIELD)
            }
        if any(not value for value in labels.values()):
            raise ValueError(f"Final consensus is incomplete for {observation_id}")
        expected = expected_inclusion(labels)
        if labels[INCLUDE_FIELD] != expected:
            raise ValueError(
                f"Final inclusion conflicts with four-check rule for {observation_id}"
            )
        final[observation_id] = labels

    if set(adjudication) != adjudication_needed:
        raise ValueError("Adjudication rows do not exactly match unresolved partial rows")
    return final


def parse_consensus_summary(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")

    def extract(pattern: str, label: str) -> str:
        match = re.search(pattern, text)
        if not match:
            raise ValueError(f"Consensus summary is missing {label}")
        return match.group(1)

    return {
        "consensus_sha256": extract(
            r"Final consensus SHA-256:\s*`([0-9a-f]{64})`",
            "final consensus SHA-256",
        ),
        "included_observations": int(extract(
            r"Included observations \(`include=yes`\):\s*\*\*(\d+)\*\*",
            "included observation count",
        )),
        "included_source_event_clusters": int(extract(
            r"Included independent source-event clusters:\s*\*\*(\d+)\*\*",
            "included source-event cluster count",
        )),
        "uncertain_observations": int(extract(
            r"Uncertain observations:\s*\*\*(\d+)\*\*",
            "uncertain observation count",
        )),
    }


def included_packet_rows(
    packet_rows: list[dict[str, str]],
    consensus: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    packet_ids = [row["review_observation_id"] for row in packet_rows]
    if len(packet_ids) != len(set(packet_ids)) or any(not value for value in packet_ids):
        raise ValueError("Sanitized packet observation IDs are blank or duplicated")
    if set(packet_ids) != set(consensus):
        raise ValueError("Final consensus IDs do not exactly match the sanitized packet")
    return [
        row for row in packet_rows
        if consensus[row["review_observation_id"]][INCLUDE_FIELD] == "yes"
    ]


def build_borrower_distribution(included_rows: list[dict[str, str]]) -> list[dict]:
    grouped = defaultdict(list)
    for row in included_rows:
        grouped[row["normalized_borrower"]].append(row)
    output = []
    for borrower, rows in sorted(grouped.items()):
        output.append({
            "normalized_borrower": borrower,
            "included_source_event_cluster_count": len({
                row["source_event_cluster_id"] for row in rows
            }),
            "included_observation_count": len(rows),
            "report_period_count": len({row["report_period_label"] for row in rows}),
            "source_ticker_count": len({row["source_ticker"] for row in rows}),
            "target_ticker_count": len({row["target_ticker"] for row in rows}),
        })
    return output


def write_distribution(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=DISTRIBUTION_FIELDS, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def materialize_final_consensus(
    path: Path,
    partial_rows: list[dict[str, str]],
    adjudication_rows: list[dict[str, str]],
) -> None:
    """Write the signed consensus in its canonical, reviewer-facing schema."""
    adjudication = {
        row["review_observation_id"]: row for row in adjudication_rows
    }
    base_fields = [
        field for field in partial_rows[0]
        if not field.startswith("consensus_")
    ]
    fieldnames = [*base_fields, *MEASUREMENT_CHECKS, INCLUDE_FIELD, "review_notes"]
    output = []
    for partial in partial_rows:
        observation_id = partial["review_observation_id"]
        unresolved = partial.get("consensus_status") == "pending_adjudication"
        adjudicated = adjudication.get(observation_id) if unresolved else None
        if unresolved and adjudicated is None:
            raise ValueError(f"Missing adjudication for {observation_id}")
        row = {field: partial.get(field, "") for field in base_fields}
        for field in (*MEASUREMENT_CHECKS, INCLUDE_FIELD):
            row[field] = (
                adjudicated[f"adjudicated_{field}"]
                if adjudicated is not None
                else partial[f"consensus_{field}"]
            )
        row["review_notes"] = (
            adjudicated["adjudication_reason"]
            if adjudicated is not None
            else partial["consensus_review_notes"]
        )
        output.append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(output)


def write_included_sample(path: Path, included_rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=INCLUDED_SAMPLE_FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(
            {field: row[field] for field in INCLUDED_SAMPLE_FIELDS}
            for row in included_rows
        )


def load_economic_id_index(path: Path) -> dict[str, dict[str, str]]:
    index = {}
    for row in read_csv(path):
        if row.get("target_current_outcome_used_for_eligibility") != "False":
            raise ValueError("Pre-reveal input reports target-current outcome use")
        if row.get("outcomes_revealed") != "False":
            raise ValueError("Pre-reveal input reports an outcome reveal")
        review_id = stable_review_id(row["observation_id"])
        if review_id in index:
            raise ValueError("Pre-reveal observation IDs are duplicated")
        index[review_id] = {
            "report_period": row["report_period_end"],
            "normalized_borrower": row["borrower_norm"],
            "source_ticker": row["source_ticker"],
            "target_ticker": row["target_ticker"],
            "source_prior_economic_facility_id": row["source_prior_facility_id"],
            "target_prior_economic_facility_id": row["target_prior_facility_id"],
        }
    return index


def build_duplicate_vote_audit(
    included_rows: list[dict[str, str]],
    packet_rows: list[dict[str, str]],
    economic_index: dict[str, dict[str, str]],
    consensus: dict[str, dict[str, str]],
    consensus_summary: dict,
    source_hashes: dict,
) -> dict:
    identities = defaultdict(list)
    for row in included_rows:
        observation_id = row["review_observation_id"]
        if observation_id not in economic_index:
            raise ValueError(f"Missing stable economic IDs for {observation_id}")
        economic = economic_index[observation_id]
        visible_values = (
            row["period_end"],
            row["normalized_borrower"],
            row["source_ticker"],
            row["target_ticker"],
        )
        if visible_values != tuple(economic[field] for field in DUPLICATE_IDENTITY_FIELDS[:4]):
            raise ValueError(f"Economic-ID join metadata conflicts for {observation_id}")
        identity = tuple(economic[field] for field in DUPLICATE_IDENTITY_FIELDS)
        identities[identity].append(row)

    duplicate_groups = [rows for rows in identities.values() if len(rows) > 1]
    blocker_groups = [
        rows for rows in duplicate_groups
        if len({row["source_event_cluster_id"] for row in rows}) > 1
    ]
    affected_observations = sorted({
        row["review_observation_id"]
        for rows in blocker_groups
        for row in rows
    })
    affected_clusters = sorted({
        row["source_event_cluster_id"]
        for rows in blocker_groups
        for row in rows
    })
    uncertain_ids = {
        observation_id for observation_id, labels in consensus.items()
        if labels[INCLUDE_FIELD] == "uncertain"
    }
    dealer_tire_uncertain = sum(
        row["review_observation_id"] in uncertain_ids
        and row["normalized_borrower"] == "dealer tire financial"
        for row in packet_rows
    )
    blocked = bool(blocker_groups)
    return {
        "status": (
            "duplicate_independent_vote_blocker"
            if blocked else "pass_no_duplicate_independent_vote"
        ),
        "phase_b_freeze_created": False,
        "target_current_structure_or_numeric_outcomes_opened": False,
        "final_event_review_consensus_sha256": consensus_summary["consensus_sha256"],
        "source_inputs": source_hashes,
        "duplicate_identity_fields": list(DUPLICATE_IDENTITY_FIELDS),
        "included_rows_checked": len(included_rows),
        "included_source_event_clusters_checked": len({
            row["source_event_cluster_id"] for row in included_rows
        }),
        "duplicate_identities_found": len(duplicate_groups),
        "different_cluster_duplicate_identities": len(blocker_groups),
        "affected_observation_ids": affected_observations,
        "affected_cluster_ids": affected_clusters,
        "uncertain_observations_retained_in_audit_trail": len(uncertain_ids),
        "dealer_tire_uncertain_rows_not_promoted": dealer_tire_uncertain,
        "automatic_merge_or_row_selection_performed": False,
    }


def validate_phase_c_packet_schema(fieldnames) -> None:
    fields = {str(field) for field in fieldnames}
    forbidden_review = sorted(fields & PHASE_A_REVIEW_COLUMNS)
    forbidden_prefixed = sorted(
        field for field in fields
        if field.startswith(("reviewer_", "adjudicated_", "consensus_", "phase_a_"))
    )
    forbidden_numeric = sorted(
        field for field in fields
        if any(token in field.lower() for token in PHASE_C_NUMERIC_FORBIDDEN_TOKENS)
    )
    forbidden = sorted(set(forbidden_review + forbidden_prefixed + forbidden_numeric))
    if forbidden:
        raise ValueError(
            "Phase C packet contains Phase A or numeric/outcome fields: "
            + ", ".join(forbidden)
        )


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--partial-consensus", type=Path, required=True)
    parser.add_argument("--adjudication", type=Path, required=True)
    parser.add_argument("--consensus-summary", type=Path, required=True)
    parser.add_argument(
        "--sanitized-packet",
        type=Path,
        default=Path("data/day4/confirmatory_event_review_blind_v2.csv"),
    )
    parser.add_argument(
        "--eligible-prefreeze",
        type=Path,
        default=Path("data/day3/eligible_prefreeze_extended.csv"),
    )
    parser.add_argument(
        "--distribution-output",
        type=Path,
        default=Path("data/day4/confirmatory_borrower_cluster_distribution.csv"),
    )
    parser.add_argument(
        "--duplicate-audit-output",
        type=Path,
        default=Path("data/day4/confirmatory_duplicate_vote_audit.json"),
    )
    parser.add_argument(
        "--final-consensus-output",
        type=Path,
        default=Path("data/day4/day4_event_review_human_consensus.csv"),
    )
    parser.add_argument(
        "--included-sample-output",
        type=Path,
        default=Path("data/day4/confirmatory_included_sample.csv"),
    )
    args = parser.parse_args()

    partial_rows = read_csv(args.partial_consensus)
    adjudication_rows = read_csv(args.adjudication)
    packet_rows = read_csv(args.sanitized_packet)
    consensus = derive_final_consensus(partial_rows, adjudication_rows)
    summary = parse_consensus_summary(args.consensus_summary)
    materialize_final_consensus(
        args.final_consensus_output,
        partial_rows,
        adjudication_rows,
    )
    if sha256_file(args.final_consensus_output) != summary["consensus_sha256"]:
        raise ValueError("Materialized consensus SHA conflicts with the signed summary")
    included = included_packet_rows(packet_rows, consensus)
    included_clusters = {
        row["source_event_cluster_id"] for row in included
    }
    uncertain_count = sum(
        labels[INCLUDE_FIELD] == "uncertain" for labels in consensus.values()
    )
    if (
        len(included) != summary["included_observations"]
        or len(included_clusters) != summary["included_source_event_clusters"]
        or uncertain_count != summary["uncertain_observations"]
    ):
        raise ValueError("Derived consensus counts conflict with the signed summary")

    distribution = build_borrower_distribution(included)
    write_included_sample(args.included_sample_output, included)
    write_distribution(args.distribution_output, distribution)
    economic_index = load_economic_id_index(args.eligible_prefreeze)
    source_hashes = {
        "partial_consensus_sha256": sha256_file(args.partial_consensus),
        "adjudication_sha256": sha256_file(args.adjudication),
        "consensus_summary_sha256": sha256_file(args.consensus_summary),
        "sanitized_packet_sha256": sha256_file(args.sanitized_packet),
        "eligible_prefreeze_sha256": sha256_file(args.eligible_prefreeze),
    }
    audit = build_duplicate_vote_audit(
        included,
        packet_rows,
        economic_index,
        consensus,
        summary,
        source_hashes,
    )
    write_json(args.duplicate_audit_output, audit)
    print(json.dumps({
        "included_observations": len(included),
        "included_source_event_clusters": len(included_clusters),
        "unique_borrowers": len(distribution),
        "maximum_clusters_from_one_borrower": max(
            (row["included_source_event_cluster_count"] for row in distribution),
            default=0,
        ),
        "duplicate_vote_status": audit["status"],
    }, sort_keys=True))
    if audit["status"] == "duplicate_independent_vote_blocker":
        raise SystemExit("duplicate_independent_vote_blocker")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Trace the two frozen Day 5 missing marks without repairing official files."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from pathlib import Path


OFFICIAL_OUTCOMES_SHA256 = "24b8b38d214580a17ea6ba6b1d2a2666d422f65d0d3f6a6bca3bd2bc5cae20ee"
AGGREGATED_CACHE_SHA256 = "4a02fc27bba48c48ded40e96d231b1487659b7733f60326796da2e7e67896925"
EXPECTED_IDS = {
    "D5EV_4bcc43807ee299de5de2ca0a",
    "D5EV_f438ca82f7a27e794a1837a9",
}
FIELDS = (
    "review_observation_id", "source_event_cluster_id", "borrower",
    "source_ticker", "target_ticker", "period", "structural_identifier",
    "missing_required_marks", "target_prior_facility_id",
    "target_current_facility_id", "target_prior_archive",
    "target_current_archive", "target_prior_accession", "target_current_accession",
    "target_prior_raw_provenance", "target_current_raw_provenance",
    "target_prior_official_principal", "target_prior_official_cost",
    "target_prior_official_fair_value", "target_current_official_principal",
    "target_current_official_cost", "target_current_official_fair_value",
    "target_prior_normalized_principal", "target_prior_normalized_cost",
    "target_prior_normalized_fair_value", "target_current_normalized_principal",
    "target_current_normalized_cost", "target_current_normalized_fair_value",
    "target_prior_aggregated_principal", "target_prior_aggregated_cost",
    "target_prior_aggregated_fair_value", "target_current_aggregated_principal",
    "target_current_aggregated_cost", "target_current_aggregated_fair_value",
    "target_prior_missing_classification", "target_current_missing_classification",
    "loss_stage", "recoverable_diagnostic_value", "recoverability",
    "classification_evidence", "post_reveal_exploratory",
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


def raw_soi_row(archive: Path, line_number: int) -> dict[str, str]:
    with zipfile.ZipFile(archive) as bundle, bundle.open("soi.tsv") as raw:
        decoded = (line.decode("utf-8-sig") for line in raw)
        reader = csv.DictReader(decoded, delimiter="\t")
        for current, row in enumerate(reader, start=2):
            if current == line_number:
                return row
    raise RuntimeError(f"SOI line {line_number} not found in {archive}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--cache", type=Path, default=Path("/private/tmp/finance-day5-sec-cache"))
    parser.add_argument("--aggregate", type=Path, default=Path("/private/tmp/finance-day5-sec-cache/bdc_facilities_2026_new_agg.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/day5_post_reveal/missing_mark_root_cause.csv"))
    args = parser.parse_args()
    repo = args.repo.resolve()
    outcomes_path = repo / "data/day5/day5_revealed_replication_outcomes.csv"
    if sha256_file(outcomes_path) != OFFICIAL_OUTCOMES_SHA256:
        raise RuntimeError("Official Day 5 outcomes changed")
    if sha256_file(args.aggregate) != AGGREGATED_CACHE_SHA256:
        raise RuntimeError("Locked aggregate cache changed")

    outcomes = {r["review_observation_id"]: r for r in read_csv(outcomes_path)}
    missing = {
        key for key, row in outcomes.items()
        if row["position_status"] == "continuing"
        and any(not row[field] for field in ("target_prior_mark", "source_prior_mark", "source_current_mark", "target_current_mark"))
    }
    if missing != EXPECTED_IDS:
        raise RuntimeError(f"Unexpected missing-mark IDs: {sorted(missing)}")
    structure = {r["review_observation_id"]: r for r in read_csv(repo / "data/day5/day5_structural_mapping_consensus.csv")}
    event_key = json.loads((repo / "private/day5/day5_event_review_key.json").read_text())["review_rows"]
    structural_key = json.loads((repo / "private/day5/day5_structural_review_evidence_key.json").read_text())["review_observation_mapping"]
    wanted = set()
    for observation_id in missing:
        wanted.add(event_key[observation_id]["target_prior_facility_id"])
        wanted.add(structural_key[observation_id]["selected_economic_facility_id"])
    aggregate = {r["economic_facility_id"]: r for r in read_csv(args.aggregate) if r["economic_facility_id"] in wanted}
    if set(aggregate) != wanted:
        raise RuntimeError("Missing facility in locked aggregate cache")

    output = []
    for observation_id in sorted(missing):
        outcome = outcomes[observation_id]
        final = structure[observation_id]
        prior = aggregate[event_key[observation_id]["target_prior_facility_id"]]
        current = aggregate[structural_key[observation_id]["selected_economic_facility_id"]]
        stage = []
        raw_rows = []
        for aggregate_row in (prior, current):
            provenance = json.loads(aggregate_row["raw_provenance_json"])
            source_ids = json.loads(aggregate_row["source_row_ids_json"])
            if len(provenance) != 1 or len(source_ids) != 1:
                raise RuntimeError("Diagnostic expected one raw lot per aggregate")
            archive_id, line_text = provenance[0].split(":")
            archive = args.cache / "raw" / f"{archive_id}_bdc.zip"
            raw = raw_soi_row(archive, int(line_text))
            normalized = {
                "principal": raw["Investment Owned, Balance, Principal Amount"],
                "cost": raw["Adjusted cost basis"],
                "fair_value": raw["Initial fair value of Investment"],
            }
            if normalized["principal"] != aggregate_row["principal"] + ".0000" and float(normalized["principal"]) != float(aggregate_row["principal"]):
                raise RuntimeError("Principal changed between SOI and aggregate")
            if float(normalized["cost"]) != float(aggregate_row["cost"]) or float(normalized["fair_value"]) != float(aggregate_row["fair_value"]):
                raise RuntimeError("Cost/fair value changed between SOI and aggregate")
            if float(normalized["principal"]) != 0 or aggregate_row["mark_fv_to_principal"]:
                raise RuntimeError("Expected disclosed zero denominator and blank mark")
            stage.append((archive_id, provenance[0], raw, normalized, aggregate_row))
            raw_rows.append(raw)
        prior_stage, current_stage = stage
        missing_fields = [field for field in ("target_prior_mark", "source_prior_mark", "source_current_mark", "target_current_mark") if not outcome[field]]
        evidence = (
            "Official SEC soi.tsv discloses principal=0.0000 at both dates; cost and fair value "
            "survive parser normalization and economic_facility_v2 unchanged. The frozen mark "
            "definition fair_value/principal is undefined at a zero denominator; no parser, join, "
            "aggregation, unit-normalization, or structural-mapping loss occurred."
        )
        output.append({
            "review_observation_id": observation_id,
            "source_event_cluster_id": outcome["source_event_cluster_id"],
            "borrower": outcome["borrower_norm"],
            "source_ticker": outcome["source_ticker"],
            "target_ticker": outcome["target_ticker"],
            "period": outcome["report_period_label"],
            "structural_identifier": final["target_current_identifier"],
            "missing_required_marks": json.dumps(missing_fields, separators=(",", ":")),
            "target_prior_facility_id": prior["economic_facility_id"],
            "target_current_facility_id": current["economic_facility_id"],
            "target_prior_archive": prior_stage[0],
            "target_current_archive": current_stage[0],
            "target_prior_accession": prior["adsh"],
            "target_current_accession": current["adsh"],
            "target_prior_raw_provenance": prior_stage[1],
            "target_current_raw_provenance": current_stage[1],
            "target_prior_official_principal": prior_stage[2]["Investment Owned, Balance, Principal Amount"],
            "target_prior_official_cost": prior_stage[2]["Adjusted cost basis"],
            "target_prior_official_fair_value": prior_stage[2]["Initial fair value of Investment"],
            "target_current_official_principal": current_stage[2]["Investment Owned, Balance, Principal Amount"],
            "target_current_official_cost": current_stage[2]["Adjusted cost basis"],
            "target_current_official_fair_value": current_stage[2]["Initial fair value of Investment"],
            "target_prior_normalized_principal": prior_stage[3]["principal"],
            "target_prior_normalized_cost": prior_stage[3]["cost"],
            "target_prior_normalized_fair_value": prior_stage[3]["fair_value"],
            "target_current_normalized_principal": current_stage[3]["principal"],
            "target_current_normalized_cost": current_stage[3]["cost"],
            "target_current_normalized_fair_value": current_stage[3]["fair_value"],
            "target_prior_aggregated_principal": prior["principal"],
            "target_prior_aggregated_cost": prior["cost"],
            "target_prior_aggregated_fair_value": prior["fair_value"],
            "target_current_aggregated_principal": current["principal"],
            "target_current_aggregated_cost": current["cost"],
            "target_current_aggregated_fair_value": current["fair_value"],
            "target_prior_missing_classification": "source_absent",
            "target_current_missing_classification": "source_absent",
            "loss_stage": "official_source_zero_principal_denominator",
            "recoverable_diagnostic_value": "",
            "recoverability": "not_recoverable_as_fv_to_principal_without_changing_mark_definition",
            "classification_evidence": evidence,
            "post_reveal_exploratory": "True",
        })
    destination = repo / args.output
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(output)
    print(json.dumps({"output": str(destination), "rows": len(output), "sha256": sha256_file(destination)}, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Apply frozen private membership after Phase A and freeze Day 5 samples.

The script reads only the outcome-blind event consensus and the Git-ignored
STRICT/SUPPORTING membership key. It does not access target-current data.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


PHASE_A_COMMIT = "88f358cbfcc0783ca54b9d8329b2d3a393702819"
CONSENSUS_SHA256 = "aef9a7d0e5fc89ef9e6d019f0ea0f1f09495089fcad74590e4747b4e27c2902b"
MEMBERSHIP_KEY_SHA256 = "6c8e142d9ff70af3bcee32a40fbbbb68ee459276d2a2ec449219123d61201733"
EVALUATOR_SHA256 = "ecc92fb08bbf18781b88a24ba44a2d2c152eb9ac2d8d62d582606b5091f73ac4"
EXPECTED_STRICT = (34, 34, 19)
EXPECTED_SUPPORTING = (75, 75, 39)

SAMPLE_FIELDS = (
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
    "overlap_day4_borrower",
    "overlap_development_borrower",
    "pre_review_layer",
    "event_review_consensus",
)

AUDIT_FIELDS = (
    "review_observation_id",
    "source_event_cluster_id",
    "period_end",
    "report_period_label",
    "normalized_borrower",
    "source_ticker",
    "target_ticker",
    "pre_review_layer",
    "human_include_for_replication",
    "included_in_strict_sample",
    "included_in_supporting_sample",
    "retained_in_audit_denominator",
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


def canonical_json_sha256(payload) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def summarize(rows: list[dict[str, str]]) -> dict:
    borrower_clusters: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        borrower_clusters[row["normalized_borrower"]].add(row["source_event_cluster_id"])
    distribution = Counter(len(clusters) for clusters in borrower_clusters.values())
    return {
        "observations": len(rows),
        "source_event_clusters": len({row["source_event_cluster_id"] for row in rows}),
        "unique_borrowers": len(borrower_clusters),
        "counts_by_period": dict(sorted(Counter(row["report_period_label"] for row in rows).items())),
        "borrower_to_cluster_distribution": {
            str(count): borrowers for count, borrowers in sorted(distribution.items())
        },
        "maximum_clusters_from_one_borrower": max((len(value) for value in borrower_clusters.values()), default=0),
    }


def validate_membership(
    consensus_rows: list[dict[str, str]],
    membership_payload: dict,
    meta: dict,
) -> tuple[set[str], set[str]]:
    review_rows = membership_payload.get("review_rows", {})
    ids = [row["review_observation_id"] for row in consensus_rows]
    if set(review_rows) != set(ids) or len(ids) != len(set(ids)):
        raise RuntimeError("Membership key IDs do not exactly match frozen consensus IDs")
    if membership_payload.get("strict_is_subset_of_supporting") is not True:
        raise RuntimeError("Private key does not assert STRICT subset relationship")
    for row in consensus_rows:
        review_id = row["review_observation_id"]
        if review_rows[review_id]["review_source_event_cluster_id"] != row["source_event_cluster_id"]:
            raise RuntimeError("Private/public source-event cluster mapping mismatch")

    strict = {review_id for review_id, value in review_rows.items() if value["strict_new_borrower"]}
    supporting = {review_id for review_id, value in review_rows.items() if value["supporting_new_fund"]}
    if not strict <= supporting:
        raise RuntimeError("STRICT is not a subset of SUPPORTING")

    row_by_id = {row["review_observation_id"]: row for row in consensus_rows}
    def description(selected: set[str]) -> tuple[int, int, int]:
        rows = [row_by_id[value] for value in selected]
        return (
            len(rows),
            len({row["source_event_cluster_id"] for row in rows}),
            len({row["normalized_borrower"] for row in rows}),
        )
    if description(strict) != EXPECTED_STRICT or description(supporting) != EXPECTED_SUPPORTING:
        raise RuntimeError("Pre-review layer counts changed")

    checks = (
        ("strict_candidate_observation_id_set", [review_rows[value]["candidate_observation_id"] for value in strict]),
        ("supporting_candidate_observation_id_set", [review_rows[value]["candidate_observation_id"] for value in supporting]),
        ("strict_source_event_cluster_set", [review_rows[value]["candidate_source_event_cluster_id"] for value in strict]),
        ("supporting_source_event_cluster_set", [review_rows[value]["candidate_source_event_cluster_id"] for value in supporting]),
        ("strict_borrower_set", [row_by_id[value]["normalized_borrower"] for value in strict]),
        ("supporting_borrower_set", [row_by_id[value]["normalized_borrower"] for value in supporting]),
    )
    for field, values in checks:
        if canonical_set_sha256(values) != meta["sha256"][field]:
            raise RuntimeError(f"Membership differs from frozen candidate hash: {field}")
    return strict, supporting


def sample_row(row: dict[str, str], key: dict, layer: str) -> dict[str, str]:
    return {
        "review_observation_id": row["review_observation_id"],
        "source_event_cluster_id": row["source_event_cluster_id"],
        "period_end": row["period_end"],
        "report_period_label": row["report_period_label"],
        "normalized_borrower": row["normalized_borrower"],
        "source_ticker": row["source_ticker"],
        "target_ticker": row["target_ticker"],
        "source_manager": row["source_manager"],
        "target_manager": row["target_manager"],
        "manager_relationship": row["manager_relationship"],
        "overlap_day4_borrower": key["overlap_day4_borrower"],
        "overlap_development_borrower": key["overlap_development_borrower"],
        "pre_review_layer": layer,
        "event_review_consensus": "yes",
    }


def duplicate_vote_record(
    included_rows: list[dict[str, str]],
    membership_rows: dict[str, dict],
) -> dict:
    identities = defaultdict(list)
    for row in included_rows:
        key = membership_rows[row["review_observation_id"]]
        identity = "|".join((
            row["period_end"], row["normalized_borrower"], row["source_ticker"],
            row["target_ticker"], key["source_prior_facility_id"],
            key["target_prior_facility_id"],
        ))
        identities[identity].append(row["source_event_cluster_id"])
    duplicates = {identity: clusters for identity, clusters in identities.items() if len(clusters) > 1}
    blockers = {
        identity: clusters for identity, clusters in duplicates.items()
        if len(set(clusters)) > 1
    }
    return {
        "status": "pass_no_duplicate_independent_vote" if not blockers else "duplicate_independent_vote_blocker",
        "included_observations_checked": len(included_rows),
        "unique_duplicate_vote_identities": len(identities),
        "duplicate_identity_count": len(duplicates),
        "independent_vote_blocker_count": len(blockers),
        "identity_definition": [
            "period_end", "normalized_borrower", "source_ticker", "target_ticker",
            "source_prior_facility_id", "target_prior_facility_id",
        ],
        "identity_set_sha256": canonical_set_sha256(identities),
        "blockers": blockers,
        "target_current_data_used": False,
    }


def final_preregistration_text(
    draft: str,
    strict_summary: dict,
    supporting_summary: dict,
    hashes: dict,
) -> str:
    prefix = draft.split("## 8. Later reveal phases", 1)[0]
    prefix = prefix.replace(
        "# Day 5 ShadowNAV replication preregistration — outcome-blind draft",
        "# Day 5 ShadowNAV replication preregistration",
        1,
    )
    prefix = prefix.replace(
        "Status: **candidate-review preparation only; not a final sample freeze**",
        "Status: **FINAL — STRICT/SUPPORTING samples frozen; Phase C/D not authorized**",
        1,
    )
    prefix = prefix.replace(
        "This document locks the Day 5 replication hierarchy, formulas, statistical procedures, decision rules, and review boundaries before any Day 5 target-current structure or numerical outcome is opened. Human event review may remove candidates under the rules below, but it may not add, replace, reclassify, or move a candidate between pre-review layers.",
        "This final document preserves the outcome-blind Day 5 replication hierarchy, formulas, statistical procedures, decision rules, and review boundaries after Phase A human consensus and Phase B sample freeze. No Day 5 target-current structure or numerical outcome had been opened at this freeze. Human review removed candidates only through the locked rules; it did not add, replace, reclassify, or move candidates between pre-review layers.",
        1,
    )
    return prefix.rstrip() + f"""

## 8. Staged reveal status

- **Phase A completed:** outcome-blind event-review consensus was frozen in Commit A `{PHASE_A_COMMIT}`.
- **Phase B completed:** the STRICT and SUPPORTING included samples are frozen with this final preregistration in the same Git commit. The commit containing these files is the required `sample_freeze_commit` in any later authorization record.
- **Phase C not yet authorized in this document:** only a separate later commit may materialize target-current non-valuation structure for exactly the frozen SUPPORTING IDs and send it to clean structural reviewers.
- **Phase D prohibited:** numeric outcomes may be opened only after structural consensus is separately frozen and a complete authorization record verifies every bound hash and commit.

The evaluator must verify its own SHA-256, the byte-frozen Day 4 statistical dependency, all bound file hashes and freeze commits, exact frozen-ID equality, STRICT subset membership, and equality between numeric-file structural labels and separately frozen structural consensus. Numeric outcomes cannot redefine structure.

## 9. Final Phase A/B frozen record

- Phase A consensus SHA-256: `{CONSENSUS_SHA256}`.
- Phase A commit: `{PHASE_A_COMMIT}`.
- STRICT included sample: {strict_summary['observations']} observations, {strict_summary['source_event_clusters']} source-event clusters, {strict_summary['unique_borrowers']} borrowers; SHA-256 `{hashes['strict_sample']}`.
- SUPPORTING included sample: {supporting_summary['observations']} observations, {supporting_summary['source_event_clusters']} source-event clusters, {supporting_summary['unique_borrowers']} borrowers; SHA-256 `{hashes['supporting_sample']}`.
- Frozen evaluator SHA-256: `{EVALUATOR_SHA256}`.
- Membership-key SHA-256: `{MEMBERSHIP_KEY_SHA256}`; the key remains Git-ignored and is not published.
- Sample-generation code SHA-256: `{hashes['generation_code']}`.
- Duplicate-vote audit SHA-256: `{hashes['duplicate_audit']}`; status `pass_no_duplicate_independent_vote`.

The pre-structural STRICT sample remains above both planning guards: at least 25 clusters and at least 15 borrowers. These are not final continuing counts; the unchanged guard is applied again after Phase C structural review.

## 10. Current prohibitions

- No target-current numeric reveal.
- No Day 5 prediction, error, MAE, effect size, p-value, bootstrap interval, or PASS/FAIL calculation.
- No result tag.
- No row replacement, supporting-to-STRICT promotion, outcome-dependent membership change, or threshold change.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--consensus", type=Path, default=Path("data/day5/day5_event_review_human_consensus.csv"))
    parser.add_argument("--membership-key", type=Path, default=Path("private/day5/day5_event_review_key.json"))
    parser.add_argument("--blind-meta", type=Path, default=Path("data/day5/day5_event_review_blind_meta.json"))
    parser.add_argument("--draft", type=Path, default=Path("docs/research/DAY5_REPLICATION_PREREGISTRATION_DRAFT.md"))
    parser.add_argument("--strict-output", type=Path, default=Path("data/day5/day5_strict_included_sample.csv"))
    parser.add_argument("--supporting-output", type=Path, default=Path("data/day5/day5_supporting_included_sample.csv"))
    parser.add_argument("--membership-audit", type=Path, default=Path("data/day5/day5_layer_membership_audit.csv"))
    parser.add_argument("--duplicate-audit", type=Path, default=Path("data/day5/day5_duplicate_vote_audit.json"))
    parser.add_argument("--freeze-json", type=Path, default=Path("data/day5/day5_replication_sample_freeze.json"))
    parser.add_argument("--freeze-doc", type=Path, default=Path("docs/research/DAY5_REPLICATION_SAMPLE_FREEZE.md"))
    parser.add_argument("--final-preregistration", type=Path, default=Path("docs/research/DAY5_REPLICATION_PREREGISTRATION.md"))
    args = parser.parse_args()

    if sha256_file(args.consensus) != CONSENSUS_SHA256:
        raise RuntimeError("Phase A consensus SHA-256 mismatch")
    if sha256_file(args.membership_key) != MEMBERSHIP_KEY_SHA256:
        raise RuntimeError("Membership-key SHA-256 mismatch")
    consensus = read_csv(args.consensus)
    membership = json.loads(args.membership_key.read_text(encoding="utf-8"))
    meta = json.loads(args.blind_meta.read_text(encoding="utf-8"))
    strict_ids, supporting_ids = validate_membership(consensus, membership, meta)
    by_id = membership["review_rows"]

    strict_rows = [
        sample_row(row, by_id[row["review_observation_id"]], "strict")
        for row in consensus
        if row["review_observation_id"] in strict_ids and row["include_for_replication"] == "yes"
    ]
    supporting_rows = [
        sample_row(
            row,
            by_id[row["review_observation_id"]],
            "strict" if row["review_observation_id"] in strict_ids else "supporting_only",
        )
        for row in consensus
        if row["review_observation_id"] in supporting_ids and row["include_for_replication"] == "yes"
    ]
    if not {row["review_observation_id"] for row in strict_rows} <= {
        row["review_observation_id"] for row in supporting_rows
    }:
        raise RuntimeError("Included STRICT is not a subset of included SUPPORTING")
    write_csv(args.strict_output, SAMPLE_FIELDS, strict_rows)
    write_csv(args.supporting_output, SAMPLE_FIELDS, supporting_rows)

    audit_rows = []
    for row in consensus:
        review_id = row["review_observation_id"]
        layer = "strict" if review_id in strict_ids else "supporting_only"
        audit_rows.append({
            "review_observation_id": review_id,
            "source_event_cluster_id": row["source_event_cluster_id"],
            "period_end": row["period_end"],
            "report_period_label": row["report_period_label"],
            "normalized_borrower": row["normalized_borrower"],
            "source_ticker": row["source_ticker"],
            "target_ticker": row["target_ticker"],
            "pre_review_layer": layer,
            "human_include_for_replication": row["include_for_replication"],
            "included_in_strict_sample": str(review_id in strict_ids and row["include_for_replication"] == "yes"),
            "included_in_supporting_sample": str(review_id in supporting_ids and row["include_for_replication"] == "yes"),
            "retained_in_audit_denominator": "True",
        })
    write_csv(args.membership_audit, AUDIT_FIELDS, audit_rows)

    included_consensus = [
        row for row in consensus
        if row["review_observation_id"] in supporting_ids and row["include_for_replication"] == "yes"
    ]
    duplicate_audit = duplicate_vote_record(included_consensus, by_id)
    if duplicate_audit["status"] != "pass_no_duplicate_independent_vote":
        raise RuntimeError("Duplicate independent-vote blocker")
    write_json(args.duplicate_audit, duplicate_audit)

    strict_summary = summarize(strict_rows)
    supporting_summary = summarize(supporting_rows)
    if (strict_summary["observations"], strict_summary["source_event_clusters"], strict_summary["unique_borrowers"]) != (31, 31, 16):
        raise RuntimeError("Derived STRICT included counts changed")
    if (supporting_summary["observations"], supporting_summary["source_event_clusters"], supporting_summary["unique_borrowers"]) != (67, 67, 33):
        raise RuntimeError("Derived SUPPORTING included counts changed")

    hashes = {
        "strict_sample": sha256_file(args.strict_output),
        "supporting_sample": sha256_file(args.supporting_output),
        "membership_audit": sha256_file(args.membership_audit),
        "duplicate_audit": sha256_file(args.duplicate_audit),
        "generation_code": sha256_file(Path(__file__).resolve()),
    }
    final_text = final_preregistration_text(
        args.draft.read_text(encoding="utf-8"), strict_summary, supporting_summary, hashes
    )
    args.final_preregistration.write_text(final_text, encoding="utf-8")
    hashes["final_preregistration"] = sha256_file(args.final_preregistration)

    layer_counts = {
        "strict": dict(Counter(
            row["include_for_replication"] for row in consensus
            if row["review_observation_id"] in strict_ids
        )),
        "supporting": dict(Counter(
            row["include_for_replication"] for row in consensus
            if row["review_observation_id"] in supporting_ids
        )),
        "supporting_only": dict(Counter(
            row["include_for_replication"] for row in consensus
            if row["review_observation_id"] in supporting_ids - strict_ids
        )),
    }
    freeze = {
        "status": "phase_b_two_layer_samples_frozen_outcome_blind",
        "freeze_date": "2026-08-15",
        "phase_a_commit": PHASE_A_COMMIT,
        "phase_a_consensus_sha256": CONSENSUS_SHA256,
        "membership_key_sha256": MEMBERSHIP_KEY_SHA256,
        "membership_key_gitignored": True,
        "strict_is_subset_of_supporting": True,
        "pre_review_counts": {
            "strict": {"observations": 34, "source_event_clusters": 34, "unique_borrowers": 19},
            "supporting": {"observations": 75, "source_event_clusters": 75, "unique_borrowers": 39},
        },
        "included_counts": {"strict": strict_summary, "supporting": supporting_summary},
        "human_consensus_counts_by_layer": layer_counts,
        "power_guard_pre_structural": {
            "minimum_continuing_clusters": 25,
            "minimum_continuing_borrowers": 15,
            "strict_current_clusters": strict_summary["source_event_clusters"],
            "strict_current_borrowers": strict_summary["unique_borrowers"],
            "guaranteed_underpowered_before_structural_review": False,
        },
        "sha256": {
            "strict_included_sample": hashes["strict_sample"],
            "supporting_included_sample": hashes["supporting_sample"],
            "ordered_strict_observation_ids": ordered_sha256(row["review_observation_id"] for row in strict_rows),
            "ordered_supporting_observation_ids": ordered_sha256(row["review_observation_id"] for row in supporting_rows),
            "strict_observation_id_set": canonical_set_sha256(row["review_observation_id"] for row in strict_rows),
            "supporting_observation_id_set": canonical_set_sha256(row["review_observation_id"] for row in supporting_rows),
            "strict_source_event_cluster_set": canonical_set_sha256(row["source_event_cluster_id"] for row in strict_rows),
            "supporting_source_event_cluster_set": canonical_set_sha256(row["source_event_cluster_id"] for row in supporting_rows),
            "strict_borrower_set": canonical_set_sha256(row["normalized_borrower"] for row in strict_rows),
            "supporting_borrower_set": canonical_set_sha256(row["normalized_borrower"] for row in supporting_rows),
            "final_preregistration": hashes["final_preregistration"],
            "evaluator": EVALUATOR_SHA256,
            "sample_generation_code": hashes["generation_code"],
            "membership_key": MEMBERSHIP_KEY_SHA256,
            "duplicate_vote_audit": hashes["duplicate_audit"],
            "membership_audit": hashes["membership_audit"],
        },
        "duplicate_vote_audit": duplicate_audit,
        "prohibitions": {
            "supporting_only_promoted_to_strict": False,
            "excluded_or_uncertain_rows_replaced": False,
            "target_current_structure_opened": False,
            "target_current_numeric_marks_opened": False,
            "predictions_errors_or_statistics_calculated": False,
            "result_status_calculated": False,
            "result_tag_created": False,
        },
    }
    write_json(args.freeze_json, freeze)

    args.freeze_doc.write_text(
        "# Day 5 two-layer replication sample freeze\n\n"
        "Status: **Phase B frozen outcome-blind; Phase C/D not yet authorized**\n\n"
        f"Commit A `{PHASE_A_COMMIT}` froze the 75-row human consensus before layer membership was opened. "
        "The verified private membership key remained Git-ignored and was then applied without changing any human label or pre-review layer.\n\n"
        "## Frozen samples\n\n"
        f"- STRICT: {strict_summary['observations']} observations, {strict_summary['source_event_clusters']} source-event clusters, {strict_summary['unique_borrowers']} borrowers; SHA-256 `{hashes['strict_sample']}`.\n"
        f"- SUPPORTING: {supporting_summary['observations']} observations, {supporting_summary['source_event_clusters']} source-event clusters, {supporting_summary['unique_borrowers']} borrowers; SHA-256 `{hashes['supporting_sample']}`.\n"
        f"- Final preregistration SHA-256: `{hashes['final_preregistration']}`.\n"
        f"- Evaluator SHA-256: `{EVALUATOR_SHA256}`.\n"
        f"- Sample-generation code SHA-256: `{hashes['generation_code']}`.\n"
        f"- Membership-key SHA-256: `{MEMBERSHIP_KEY_SHA256}` (key not committed).\n"
        f"- Duplicate-vote audit SHA-256: `{hashes['duplicate_audit']}`; no blocker.\n\n"
        "STRICT remains a subset of SUPPORTING. The locked human rule excluded all `no` and `uncertain` rows without replacement. No supporting-only row was promoted into STRICT. The pre-structural STRICT sample has 31 clusters and 16 borrowers, so it is not already guaranteed underpowered; the unchanged 25-cluster/15-borrower guard is applied again after structural review.\n\n"
        "No target-current structure or valuation value was opened in this commit. No prediction, error, MAE, p-value, bootstrap interval, result status, or tag was created.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

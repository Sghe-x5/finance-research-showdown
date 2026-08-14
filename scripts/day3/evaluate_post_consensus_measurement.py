#!/usr/bin/env python3
"""Evaluate frozen human consensus against private blind-design mappings.

This script is deliberately limited to measurement validation. It reads no
eligible-nowcast table, target-current mark, price return, or target outcome.
Private row-level mappings are used locally and only aggregate results are
written to Git-visible outputs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


CONSENSUS_FREEZE_COMMIT = "f6abde5700ae1afc20d342cad335112fdd156817"
FACILITY_LABELS = {
    "same_facility",
    "same_borrower_different_facility",
    "uncertain",
    "unrelated",
}
ALIAS_BORROWER_LABELS = {"yes", "no", "uncertain"}
ALIAS_FACILITY_LABELS = {"yes", "no", "uncertain", "not_applicable"}
MISSING = {"", "unknown", "n/a", "na", "none", "null"}
EVIDENCE_FIELDS = (
    "debt_equity",
    "facility_type",
    "lien",
    "currency",
    "reference_rate",
    "spread",
    "maturity",
    "funded_status",
    "acquisition_date",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_unique(rows: list[dict], field: str, expected: int) -> dict[str, dict]:
    if len(rows) != expected:
        raise RuntimeError(f"{field}: expected {expected} rows, found {len(rows)}")
    keyed = {row[field]: row for row in rows}
    if len(keyed) != expected or "" in keyed:
        raise RuntimeError(f"{field}: IDs are blank or duplicated")
    return keyed


def is_observed(value: str | None) -> bool:
    return (value or "").strip().lower() not in MISSING


def ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def wilson_interval(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if trials <= 0:
        raise ValueError("Wilson interval requires a positive denominator")
    p = successes / trials
    denominator = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denominator
    half = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)


def binomial_upper_tail(successes: int, trials: int, probability: float) -> float:
    return sum(
        math.comb(trials, index)
        * probability**index
        * (1 - probability) ** (trials - index)
        for index in range(successes, trials + 1)
    )


def exact_one_sided_lower(successes: int, trials: int, alpha: float = 0.05) -> float:
    """Clopper-Pearson one-sided lower confidence bound."""
    if trials <= 0 or not 0 <= successes <= trials:
        raise ValueError("Invalid binomial counts")
    if successes == 0:
        return 0.0
    low, high = 0.0, successes / trials
    for _ in range(100):
        midpoint = (low + high) / 2
        if binomial_upper_tail(successes, trials, midpoint) < alpha:
            low = midpoint
        else:
            high = midpoint
    return (low + high) / 2


def manager_lookup(path: Path) -> dict[str, str]:
    rows = read_csv(path)
    lookup = {row["ticker"]: row["canonical_manager"] for row in rows}
    if len(lookup) != 19 or any(not value for value in lookup.values()):
        raise RuntimeError("Canonical manager map is incomplete")
    return lookup


def manager_relationship(row: dict[str, str], managers: dict[str, str]) -> tuple[str, str, str]:
    left = managers[row["left_ticker"]]
    right = managers[row["right_ticker"]]
    relationship = "same_manager" if left == right else "cross_manager"
    return left, right, relationship


def informative_count(row: dict[str, str]) -> int:
    return sum(
        is_observed(row.get(f"left_{field}")) and is_observed(row.get(f"right_{field}"))
        for field in EVIDENCE_FIELDS
    )


def known_conflict(left: str, right: str) -> bool:
    return is_observed(left) and is_observed(right) and left.strip().lower() != right.strip().lower()


def primary_false_positive_reason(row: dict[str, str]) -> str:
    if known_conflict(row["left_debt_equity"], row["right_debt_equity"]):
        return "debt_equity_conflict"
    if known_conflict(row["left_lien"], row["right_lien"]):
        return "lien_conflict"
    if known_conflict(row["left_facility_type"], row["right_facility_type"]):
        return "facility_type_conflict"
    if is_observed(row["left_spread"]) and is_observed(row["right_spread"]):
        if abs(float(row["left_spread"]) - float(row["right_spread"])) > 0.0025 + 1e-12:
            return "spread_conflict_over_25bp"
    return "other_or_insufficient_official_fields"


def metric_row(rows: list[dict]) -> dict:
    labels = Counter(row["manual_label"] for row in rows)
    true_positive = labels["same_facility"]
    false_positive = labels["same_borrower_different_facility"] + labels["unrelated"]
    unresolved = labels["uncertain"]
    resolved = true_positive + false_positive
    output = {
        "sample_rows": len(rows),
        "true_positive": true_positive,
        "definite_false_positive": false_positive,
        "unresolved": unresolved,
        "conditional_precision_resolved": ratio(true_positive, resolved),
        "strict_confirmation_rate": ratio(true_positive, len(rows)),
        "definite_resolution_coverage": ratio(resolved, len(rows)),
        "uncertain_rate": ratio(unresolved, len(rows)),
    }
    if resolved:
        low, high = wilson_interval(true_positive, resolved)
        output["conditional_precision_wilson_two_sided_95"] = {"lower": low, "upper": high}
        output["conditional_precision_exact_one_sided_95_lower"] = exact_one_sided_lower(
            true_positive, resolved
        )
    return output


def evaluate_facility(
    blind_path: Path,
    consensus_path: Path,
    private_path: Path,
    manager_map_path: Path,
) -> tuple[dict, list[dict], list[dict], list[dict]]:
    blind = require_unique(read_csv(blind_path), "blind_pair_id", 120)
    consensus = require_unique(read_csv(consensus_path), "blind_pair_id", 120)
    private_payload = json.loads(private_path.read_text(encoding="utf-8"))
    private = require_unique(private_payload["rows"], "blind_pair_id", 120)
    if set(blind) != set(consensus) or set(blind) != set(private):
        raise RuntimeError("Facility blind, consensus, and private IDs do not match")
    managers = manager_lookup(manager_map_path)
    joined = []
    for pair_id in blind:
        public = blind[pair_id]
        human = consensus[pair_id]
        hidden = private[pair_id]
        if human["manual_label"] not in FACILITY_LABELS:
            raise RuntimeError(f"Invalid facility consensus label: {human['manual_label']}")
        if any(public[field] != human[field] for field in public if field not in {"manual_label", "label_notes"}):
            raise RuntimeError(f"Consensus changed non-review facility fields: {pair_id}")
        left_manager, right_manager, relationship = manager_relationship(public, managers)
        joined.append({
            **public,
            "manual_label": human["manual_label"],
            "hidden_stratum": hidden["hidden_stratum"],
            "left_manager": left_manager,
            "right_manager": right_manager,
            "manager_relationship": relationship,
            "informative_field_count": informative_count(public),
        })

    stratum_counts = Counter(row["hidden_stratum"] for row in joined)
    expected = {
        "predicted_same_facility_high": 60,
        "hard_same_borrower_different_facility": 30,
        "uncertain_alias_distractor": 30,
    }
    if dict(stratum_counts) != expected:
        raise RuntimeError(f"Unexpected hidden-stratum counts: {stratum_counts}")

    positive = [row for row in joined if row["hidden_stratum"] == "predicted_same_facility_high"]
    primary = metric_row(positive)
    point = primary["conditional_precision_resolved"] or 0.0
    if point < 0.95:
        status = "MEASUREMENT_FAIL_POINT_PRECISION_BELOW_95_PERCENT"
    else:
        status = "MEASUREMENT_INCONCLUSIVE_REQUIRES_HUMAN_INTERPRETATION"

    confusion_counts = Counter((row["hidden_stratum"], row["manual_label"]) for row in joined)
    confusion = []
    for stratum in expected:
        for label in sorted(FACILITY_LABELS):
            count = confusion_counts[(stratum, label)]
            confusion.append({
                "hidden_stratum": stratum,
                "human_consensus_label": label,
                "count": count,
                "stratum_rows": expected[stratum],
                "share_within_stratum": count / expected[stratum],
            })

    false_positives = [
        row for row in positive
        if row["manual_label"] in {"same_borrower_different_facility", "unrelated"}
    ]
    reason_counts = Counter(primary_false_positive_reason(row) for row in false_positives)
    reason_definitions = {
        "debt_equity_conflict": "Both official fields are observed and debt/equity classes conflict.",
        "lien_conflict": "Both official lien fields are observed and conflict.",
        "facility_type_conflict": "Both official facility-type fields are observed and conflict.",
        "spread_conflict_over_25bp": "Both spreads are observed and differ by more than 25 basis points.",
        "other_or_insufficient_official_fields": "No preceding structured-field conflict explains the human nonmatch.",
    }
    fp_audit = [
        {
            "primary_conflict_reason": reason,
            "definite_false_positive_count": reason_counts[reason],
            "share_of_definite_false_positives": ratio(reason_counts[reason], len(false_positives)),
            "definition": reason_definitions[reason],
        }
        for reason in reason_definitions
    ]

    manager_breakdown = {}
    for relationship in ("same_manager", "cross_manager"):
        manager_breakdown[relationship] = metric_row([
            row for row in positive if row["manager_relationship"] == relationship
        ])
    pair_groups = defaultdict(list)
    for row in positive:
        pair = " | ".join(sorted((row["left_manager"], row["right_manager"])))
        pair_groups[pair].append(row)
    manager_pairs = [
        {"manager_pair": pair, **metric_row(rows)}
        for pair, rows in sorted(pair_groups.items())
    ]
    manager_confusion_counts = Counter(
        (row["manager_relationship"], row["hidden_stratum"], row["manual_label"])
        for row in joined
    )
    manager_confusion = [
        {
            "manager_relationship": relationship,
            "hidden_stratum": stratum,
            "human_consensus_label": label,
            "count": manager_confusion_counts[(relationship, stratum, label)],
        }
        for relationship in ("same_manager", "cross_manager")
        for stratum in expected
        for label in sorted(FACILITY_LABELS)
    ]

    evidence_groups = defaultdict(list)
    for row in positive:
        evidence_groups[row["informative_field_count"]].append(row)
    evidence = [
        {"informative_official_field_count": count, **metric_row(rows)}
        for count, rows in sorted(evidence_groups.items())
    ]

    payload = {
        "benchmark": "facility_blind_v3_post_consensus_measurement",
        "consensus_freeze_commit": CONSENSUS_FREEZE_COMMIT,
        "input_integrity": {
            "blind_file_sha256": sha256_file(blind_path),
            "consensus_file_sha256": sha256_file(consensus_path),
            "private_key_sha256_verified_locally": sha256_file(private_path),
            "manager_map_sha256": sha256_file(manager_map_path),
            "private_row_level_mapping_published": False,
        },
        "primary_hidden_stratum": "predicted_same_facility_high",
        "primary_measurement": primary,
        "measurement_status": status,
        "decision_rule": {
            "point_precision_threshold": 0.95,
            "target_reveal_automatically_authorized": False,
        },
        "same_manager_vs_cross_manager": manager_breakdown,
        "all_sample_manager_relationship_confusion": manager_confusion,
        "manager_pair_metrics": manager_pairs,
        "evidence_completeness": {
            "fields": list(EVIDENCE_FIELDS),
            "positive_stratum_buckets": evidence,
        },
        "false_positive_primary_reason_counts": dict(sorted(reason_counts.items())),
        "abstention": {
            "model_positive_human_uncertain_count": primary["unresolved"],
            "model_positive_human_uncertain_rate": primary["uncertain_rate"],
        },
        "scope_statement": "Recall is conditional on the generated candidate universe and is not population recall.",
        "research_boundaries": {
            "target_outcomes_read": False,
            "target_same_quarter_marks_read": False,
            "target_error_metrics_calculated": False,
            "universe_expanded": False,
            "results_tag_created": False,
            "human_consensus_labels_modified": False,
        },
    }
    return payload, confusion, fp_audit, manager_pairs


def evaluate_alias(
    blind_path: Path,
    consensus_path: Path,
    private_path: Path,
) -> tuple[dict, list[dict], list[dict]]:
    blind = require_unique(read_csv(blind_path), "blind_alias_id", 128)
    consensus = require_unique(read_csv(consensus_path), "blind_alias_id", 128)
    private_payload = json.loads(private_path.read_text(encoding="utf-8"))
    private = require_unique(private_payload["rows"], "blind_alias_id", 128)
    if set(blind) != set(consensus) or set(blind) != set(private):
        raise RuntimeError("Alias blind, consensus, and private IDs do not match")

    joined = []
    review_fields = {"manual_same_borrower", "manual_same_facility", "review_notes"}
    for alias_id in blind:
        public = blind[alias_id]
        human = consensus[alias_id]
        hidden = private[alias_id]
        borrower_label = human["manual_same_borrower"]
        facility_label = human["manual_same_facility"]
        if borrower_label not in ALIAS_BORROWER_LABELS or facility_label not in ALIAS_FACILITY_LABELS:
            raise RuntimeError(f"Invalid alias consensus label: {alias_id}")
        if any(public[field] != human[field] for field in public if field not in review_fields):
            raise RuntimeError(f"Consensus changed non-review alias fields: {alias_id}")
        nonblank = bool(public["candidate_ticker"].strip())
        joined.append({
            **public,
            "manual_same_borrower": borrower_label,
            "manual_same_facility": facility_label,
            "candidate_nonblank": nonblank,
            "exact_borrower_block": bool(hidden["exact_borrower_block"]),
        })

    nonblank = [row for row in joined if row["candidate_nonblank"]]
    blank = [row for row in joined if not row["candidate_nonblank"]]
    if len(nonblank) != 91 or len(blank) != 37:
        raise RuntimeError(f"Unexpected alias observation counts: {len(nonblank)} nonblank, {len(blank)} blank")
    if any(row["manual_same_borrower"] != "uncertain" for row in blank):
        raise RuntimeError("Blank alias rows must remain non-observations labeled uncertain")

    borrower_counts = Counter(row["manual_same_borrower"] for row in nonblank)
    resolved = borrower_counts["yes"] + borrower_counts["no"]
    borrower_metrics = {
        "nonblank_candidate_rows": len(nonblank),
        "confirmed_same_borrower": borrower_counts["yes"],
        "definite_nonmatch": borrower_counts["no"],
        "unresolved": borrower_counts["uncertain"],
        "resolved_candidate_precision": ratio(borrower_counts["yes"], resolved),
        "resolution_coverage": ratio(resolved, len(nonblank)),
        "uncertain_rate": ratio(borrower_counts["uncertain"], len(nonblank)),
    }

    confusion_counts = Counter(
        (
            "inside_exact_name_block" if row["exact_borrower_block"] else "outside_exact_name_block",
            row["manual_same_borrower"],
        )
        for row in nonblank
    )
    confusion = []
    for scope in ("inside_exact_name_block", "outside_exact_name_block"):
        scope_total = sum(count for (candidate_scope, _), count in confusion_counts.items() if candidate_scope == scope)
        for label in sorted(ALIAS_BORROWER_LABELS):
            count = confusion_counts[(scope, label)]
            confusion.append({
                "candidate_scope": scope,
                "human_same_borrower_consensus": label,
                "count": count,
                "scope_rows": scope_total,
                "share_within_scope": ratio(count, scope_total),
            })

    grouped = defaultdict(list)
    for row in joined:
        grouped[(row["source_ticker"], row["source_borrower_norm"])].append(row)
    if len(grouped) != 30:
        raise RuntimeError(f"Expected 30 alias borrower groups, found {len(grouped)}")
    group_rows = []
    for (source_ticker, borrower), rows in sorted(grouped.items()):
        observed = [row for row in rows if row["candidate_nonblank"]]
        labels = Counter(row["manual_same_borrower"] for row in observed)
        outside_yes = sum(
            row["manual_same_borrower"] == "yes" and not row["exact_borrower_block"]
            for row in observed
        )
        if not observed:
            status = "no_candidate_observed"
        elif labels["yes"]:
            status = "at_least_one_confirmed_alias"
        elif labels["uncertain"]:
            status = "unresolved_candidate_set"
        else:
            status = "only_definite_nonmatches"
        group_rows.append({
            "source_group_id": hashlib.sha256(
                f"{source_ticker}|{borrower}".encode("utf-8")
            ).hexdigest()[:20],
            "source_ticker": source_ticker,
            "source_borrower_norm": borrower,
            "candidate_rows": len(observed),
            "confirmed_alias_rows": labels["yes"],
            "definite_nonmatch_rows": labels["no"],
            "unresolved_rows": labels["uncertain"],
            "group_status": status,
            "confirmed_alias_outside_exact_block_rows": outside_yes,
            "lower_bound_exact_block_miss": bool(outside_yes),
        })

    group_counts = Counter(row["group_status"] for row in group_rows)
    lower_bound_groups = sum(row["lower_bound_exact_block_miss"] for row in group_rows)
    confirmed_alias_rows = [row for row in nonblank if row["manual_same_borrower"] == "yes"]
    facility_counts = Counter(row["manual_same_facility"] for row in confirmed_alias_rows)
    payload = {
        "benchmark": "alias_blind_post_consensus_measurement",
        "consensus_freeze_commit": CONSENSUS_FREEZE_COMMIT,
        "input_integrity": {
            "blind_file_sha256": sha256_file(blind_path),
            "consensus_file_sha256": sha256_file(consensus_path),
            "private_key_sha256_verified_locally": sha256_file(private_path),
            "private_row_level_mapping_published": False,
        },
        "row_level_borrower_alias_measurement": borrower_metrics,
        "blank_candidate_policy": {
            "blank_candidate_rows": len(blank),
            "classification": "non_observation",
            "included_in_metric_denominators": False,
            "counted_as_true_negatives": False,
        },
        "group_level_30_borrowers": {
            "sampled_source_borrowers": len(group_rows),
            "status_counts": dict(sorted(group_counts.items())),
            "groups_with_confirmed_alias_outside_exact_block": lower_bound_groups,
            "lower_bound_alias_loss_rate_over_all_sampled_groups": lower_bound_groups / len(group_rows),
        },
        "facility_identity_within_confirmed_borrower_aliases": {
            "confirmed_alias_rows": len(confirmed_alias_rows),
            "same_facility_yes": facility_counts["yes"],
            "same_facility_no": facility_counts["no"],
            "same_facility_uncertain": facility_counts["uncertain"],
        },
        "scope_statement": "Recall is conditional on the generated candidate universe and is not population recall.",
        "research_boundaries": {
            "target_outcomes_read": False,
            "target_same_quarter_marks_read": False,
            "universe_expanded": False,
            "human_consensus_labels_modified": False,
        },
    }
    return payload, group_rows, confusion


def percent(value: float | None) -> str:
    return "n/a" if value is None else f"{100 * value:.1f}%"


def render_report(facility: dict, alias: dict) -> str:
    primary = facility["primary_measurement"]
    same = facility["same_manager_vs_cross_manager"]["same_manager"]
    cross = facility["same_manager_vs_cross_manager"]["cross_manager"]
    alias_rows = alias["row_level_borrower_alias_measurement"]
    alias_groups = alias["group_level_30_borrowers"]
    interval = primary["conditional_precision_wilson_two_sided_95"]
    facility_identity = alias["facility_identity_within_confirmed_borrower_aliases"]
    return f"""# Blind Measurement Benchmark Results

## Research boundary

The independent human consensus was frozen in commit `{CONSENSUS_FREEZE_COMMIT}` before the private design mappings were opened. The mappings were read only from ignored local files, their SHA-256 values were verified, and no row-level hidden mapping is published here. Human labels were not changed.

This is a measurement benchmark only. No ShadowNAV target outcome, target same-quarter mark, stock return, or target-error metric was opened or calculated. The fund universe was not expanded, no nowcast sample was frozen, and no results tag was created.

## Facility benchmark

The primary model-positive stratum contained 60 hidden `predicted_same_facility_high` pairs. Human consensus classified {primary['true_positive']} as the same facility, {primary['definite_false_positive']} as definite false positives, and {primary['unresolved']} as uncertain.

- Conditional precision among resolved pairs: **{percent(primary['conditional_precision_resolved'])}** ({primary['true_positive']}/{primary['true_positive'] + primary['definite_false_positive']}).
- Strict confirmation rate over all 60 model-positive pairs: **{percent(primary['strict_confirmation_rate'])}**.
- Definite-resolution coverage: **{percent(primary['definite_resolution_coverage'])}**.
- Human-uncertain/abstention rate: **{percent(primary['uncertain_rate'])}**.
- Wilson two-sided 95% interval for conditional precision: **{percent(interval['lower'])}–{percent(interval['upper'])}**.
- Exact one-sided 95% lower bound: **{percent(primary['conditional_precision_exact_one_sided_95_lower'])}**.
- Status: **{facility['measurement_status']}**.

The point estimate is tested against the preregistered 95% precision gate. An uncertain human consensus is not silently converted into either a true or false positive: it lowers coverage and remains in the strict denominator.

### Manager split within the model-positive stratum

| Relationship | Rows | TP | Definite FP | Uncertain | Conditional precision | Coverage |
|---|---:|---:|---:|---:|---:|---:|
| Same manager | {same['sample_rows']} | {same['true_positive']} | {same['definite_false_positive']} | {same['unresolved']} | {percent(same['conditional_precision_resolved'])} | {percent(same['definite_resolution_coverage'])} |
| Cross manager | {cross['sample_rows']} | {cross['true_positive']} | {cross['definite_false_positive']} | {cross['unresolved']} | {percent(cross['conditional_precision_resolved'])} | {percent(cross['definite_resolution_coverage'])} |

The manager relationship uses the canonical 19-fund manager map. Manager-pair and official-evidence-completeness breakdowns are stored as aggregates in `facility_blind_evaluation.json`; no blind pair IDs or private candidate IDs are exposed.

False-positive composition is reported in `facility_false_positive_audit.csv`. Categories are assigned deterministically from the public official fields, with one primary reason per definite false positive.

Recall is conditional on the generated candidate universe and is not population recall.

## Alias benchmark

The alias file contained 128 rows. Its 37 blank candidate rows are **non-observations**: they are excluded from the 91-row nonblank denominator and are not true negatives.

- Confirmed same-borrower aliases among nonblank rows: **{alias_rows['confirmed_same_borrower']}**.
- Definite nonmatches: **{alias_rows['definite_nonmatch']}**.
- Unresolved: **{alias_rows['unresolved']}**.
- Resolved-candidate precision: **{percent(alias_rows['resolved_candidate_precision'])}**.
- Resolution coverage: **{percent(alias_rows['resolution_coverage'])}**.
- Uncertain rate: **{percent(alias_rows['uncertain_rate'])}**.

Across the 30 preselected borrower groups, {alias_groups['status_counts'].get('at_least_one_confirmed_alias', 0)} had at least one confirmed alias, {alias_groups['status_counts'].get('only_definite_nonmatches', 0)} had only definite nonmatches, {alias_groups['status_counts'].get('unresolved_candidate_set', 0)} remained unresolved, and {alias_groups['status_counts'].get('no_candidate_observed', 0)} had no candidate observation. Confirmed aliases outside exact-name blocking occurred in {alias_groups['groups_with_confirmed_alias_outside_exact_block']}/30 groups, a conservative lower-bound loss rate of {percent(alias_groups['lower_bound_alias_loss_rate_over_all_sampled_groups'])}.

Within the {facility_identity['confirmed_alias_rows']} confirmed borrower-alias rows, facility identity was confirmed for {facility_identity['same_facility_yes']}, rejected for {facility_identity['same_facility_no']}, and unresolved for {facility_identity['same_facility_uncertain']}.

Recall is conditional on the generated candidate universe and is not population recall.

## Interpretation and next boundary

These outputs validate or reject the measurement layer only. They do not authorize a ShadowNAV target reveal automatically. Any later target reveal still requires a separate human decision, an approved preregistration, adequate power, and the required matching interpretation.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--facility-blind", type=Path, default=Path("data/day3/blind_facility_pairs_v3.csv"))
    parser.add_argument("--facility-consensus", type=Path, default=Path("data/day3/human_consensus_facility_labels_v3.csv"))
    parser.add_argument("--facility-private", type=Path, default=Path("private/day3/blind_facility_v3_key.json"))
    parser.add_argument("--alias-blind", type=Path, default=Path("data/day3/blind_alias_candidates.csv"))
    parser.add_argument("--alias-consensus", type=Path, default=Path("data/day3/human_consensus_alias_labels.csv"))
    parser.add_argument("--alias-private", type=Path, default=Path("private/day3/blind_alias_key.json"))
    parser.add_argument("--manager-map", type=Path, default=Path("data/day3/bdc_manager_map.csv"))
    args = parser.parse_args()

    facility, facility_confusion, fp_audit, _ = evaluate_facility(
        args.facility_blind,
        args.facility_consensus,
        args.facility_private,
        args.manager_map,
    )
    alias, alias_groups, alias_confusion = evaluate_alias(
        args.alias_blind,
        args.alias_consensus,
        args.alias_private,
    )
    write_json(Path("data/day3/facility_blind_evaluation.json"), facility)
    write_csv(
        Path("data/day3/facility_hidden_stratum_confusion.csv"),
        facility_confusion,
        ["hidden_stratum", "human_consensus_label", "count", "stratum_rows", "share_within_stratum"],
    )
    write_csv(
        Path("data/day3/facility_false_positive_audit.csv"),
        fp_audit,
        ["primary_conflict_reason", "definite_false_positive_count", "share_of_definite_false_positives", "definition"],
    )
    write_json(Path("data/day3/alias_blind_evaluation.json"), alias)
    write_csv(
        Path("data/day3/alias_group_level_results.csv"),
        alias_groups,
        [
            "source_group_id", "source_ticker", "source_borrower_norm", "candidate_rows",
            "confirmed_alias_rows", "definite_nonmatch_rows", "unresolved_rows", "group_status",
            "confirmed_alias_outside_exact_block_rows", "lower_bound_exact_block_miss",
        ],
    )
    write_csv(
        Path("data/day3/alias_nonblank_confusion.csv"),
        alias_confusion,
        ["candidate_scope", "human_same_borrower_consensus", "count", "scope_rows", "share_within_scope"],
    )
    Path("docs/research/BLIND_BENCHMARK_RESULTS.md").write_text(
        render_report(facility, alias), encoding="utf-8"
    )
    print(json.dumps({
        "facility": facility["primary_measurement"],
        "facility_status": facility["measurement_status"],
        "alias_nonblank": alias["row_level_borrower_alias_measurement"],
        "alias_groups": alias["group_level_30_borrowers"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

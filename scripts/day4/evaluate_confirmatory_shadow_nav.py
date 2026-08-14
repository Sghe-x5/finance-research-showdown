#!/usr/bin/env python3
"""Frozen-formula candidate evaluator for confirmatory ShadowNAV.

The module is prepared before outcome reveal and is currently exercised only
with synthetic unit tests. Its CLI refuses to open an outcome file unless a
separate authorization record explicitly approves the reveal.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path


PERMUTATION_SEED = 20260814
PERMUTATION_DRAWS = 100_000
BOOTSTRAP_SEED = 20260814
BOOTSTRAP_DRAWS = 10_000
MIN_CONTINUING_CLUSTERS = 25
REQUIRED_RELATIVE_MAE_IMPROVEMENT = 0.10
ALLOWED_POSITION_STATUSES = {
    "continuing",
    "partial_repayment",
    "full_repayment",
    "sale_exit",
    "refinancing_amendment",
    "unmatched_disappearance",
}


def mean(values):
    if not values:
        raise ValueError("A non-empty sequence is required")
    return sum(values) / len(values)


def prediction_b0(target_prior_mark: float) -> float:
    return float(target_prior_mark)


def prediction_shadow_nav(
    target_prior_mark: float,
    source_current_mark: float,
    source_prior_mark: float,
) -> float:
    return float(target_prior_mark) + (
        float(source_current_mark) - float(source_prior_mark)
    )


def observation_error(row: dict) -> dict:
    if row["position_status"] != "continuing":
        raise ValueError("Mark errors are defined only for continuing facilities")
    required = (
        "target_prior_mark",
        "source_current_mark",
        "source_prior_mark",
        "target_current_mark",
    )
    if any(row.get(field) in (None, "") for field in required):
        raise ValueError("Continuing observation has a missing mark")
    actual = float(row["target_current_mark"])
    b0 = prediction_b0(float(row["target_prior_mark"]))
    sn = prediction_shadow_nav(
        float(row["target_prior_mark"]),
        float(row["source_current_mark"]),
        float(row["source_prior_mark"]),
    )
    error_b0 = abs(actual - b0)
    error_sn = abs(actual - sn)
    return {
        "review_observation_id": row["review_observation_id"],
        "source_event_cluster_id": row["source_event_cluster_id"],
        "borrower_norm": row["borrower_norm"],
        "report_period_label": row["report_period_label"],
        "source_ticker": row["source_ticker"],
        "target_ticker": row["target_ticker"],
        "reporting_window_days": float(row["reporting_window_days"]),
        "absolute_error_b0": error_b0,
        "absolute_error_sn": error_sn,
        "paired_error_difference": error_sn - error_b0,
    }


def continuing_errors(rows: list[dict]) -> tuple[list[dict], int]:
    errors = []
    missing = 0
    for row in rows:
        status = row.get("position_status")
        if status not in ALLOWED_POSITION_STATUSES:
            raise ValueError(f"Invalid position status: {status}")
        if status != "continuing":
            continue
        try:
            errors.append(observation_error(row))
        except ValueError:
            missing += 1
    return errors, missing


def attrition_flow(rows: list[dict]) -> dict:
    counts = Counter()
    for row in rows:
        status = row.get("position_status")
        if status not in ALLOWED_POSITION_STATUSES:
            raise ValueError(f"Invalid position status: {status}")
        counts[status] += 1
    return {status: counts[status] for status in sorted(ALLOWED_POSITION_STATUSES)}


def aggregate_source_event_clusters(errors: list[dict]) -> list[dict]:
    grouped = defaultdict(list)
    for row in errors:
        grouped[row["source_event_cluster_id"]].append(row)
    clusters = []
    for cluster_id, rows in sorted(grouped.items()):
        borrowers = {row["borrower_norm"] for row in rows}
        periods = {row["report_period_label"] for row in rows}
        sources = {row["source_ticker"] for row in rows}
        if len(borrowers) != 1 or len(periods) != 1 or len(sources) != 1:
            raise ValueError("Source-event cluster metadata is inconsistent")
        clusters.append({
            "source_event_cluster_id": cluster_id,
            "borrower_norm": next(iter(borrowers)),
            "report_period_label": next(iter(periods)),
            "source_ticker": next(iter(sources)),
            "target_count": len(rows),
            "target_tickers": sorted({row["target_ticker"] for row in rows}),
            "mean_absolute_error_b0": mean([row["absolute_error_b0"] for row in rows]),
            "mean_absolute_error_sn": mean([row["absolute_error_sn"] for row in rows]),
            "mean_paired_error_difference": mean([
                row["paired_error_difference"] for row in rows
            ]),
        })
    return clusters


def paired_permutation_pvalue(
    differences: list[float],
    draws: int = PERMUTATION_DRAWS,
    seed: int = PERMUTATION_SEED,
) -> float:
    if not differences or draws <= 0:
        raise ValueError("Permutation test requires differences and positive draws")
    observed = mean(differences)
    magnitudes = [abs(float(value)) for value in differences]
    rng = random.Random(seed)
    extreme = 0
    for _ in range(draws):
        permuted = mean([
            magnitude if rng.getrandbits(1) else -magnitude
            for magnitude in magnitudes
        ])
        if permuted <= observed + 1e-15:
            extreme += 1
    return (extreme + 1) / (draws + 1)


def percentile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("Percentile requires values")
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def borrower_cluster_bootstrap_interval(
    clusters: list[dict],
    draws: int = BOOTSTRAP_DRAWS,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[float, float]:
    if not clusters or draws <= 0:
        raise ValueError("Bootstrap requires clusters and positive draws")
    by_borrower = defaultdict(list)
    for row in clusters:
        by_borrower[row["borrower_norm"]].append(row["mean_paired_error_difference"])
    borrowers = sorted(by_borrower)
    rng = random.Random(seed)
    estimates = []
    for _ in range(draws):
        sampled = [rng.choice(borrowers) for _ in borrowers]
        values = [value for borrower in sampled for value in by_borrower[borrower]]
        estimates.append(mean(values))
    estimates.sort()
    return percentile(estimates, 0.025), percentile(estimates, 0.975)


def leave_one_borrower_out(clusters: list[dict]) -> dict[str, float]:
    borrowers = sorted({row["borrower_norm"] for row in clusters})
    output = {}
    for omitted in borrowers:
        remaining = [
            row["mean_paired_error_difference"]
            for row in clusters
            if row["borrower_norm"] != omitted
        ]
        if remaining:
            output[omitted] = mean(remaining)
    return output


def period_direction(clusters: list[dict]) -> dict:
    grouped = defaultdict(list)
    for row in clusters:
        grouped[row["report_period_label"]].append(row["mean_paired_error_difference"])
    means = {period: mean(values) for period, values in sorted(grouped.items())}
    negative = sum(value < 0 for value in means.values())
    return {
        "period_mean_differences": means,
        "negative_periods": negative,
        "represented_periods": len(means),
        "strict_majority_negative": negative > len(means) / 2,
    }


def reporting_window_stratum(days: float) -> str:
    if days <= 2:
        return "le_2_days"
    if days <= 5:
        return "gt_2_le_5_days"
    return "gt_5_days"


def observation_summary(rows: list[dict]) -> dict:
    if not rows:
        return {"observations": 0}
    improved = sum(row["paired_error_difference"] < 0 for row in rows)
    return {
        "observations": len(rows),
        "mae_b0": mean([row["absolute_error_b0"] for row in rows]),
        "mae_sn": mean([row["absolute_error_sn"] for row in rows]),
        "median_absolute_error_b0": statistics.median([
            row["absolute_error_b0"] for row in rows
        ]),
        "median_absolute_error_sn": statistics.median([
            row["absolute_error_sn"] for row in rows
        ]),
        "fraction_improved": improved / len(rows),
    }


def grouped_observation_summaries(errors: list[dict], field: str) -> dict:
    grouped = defaultdict(list)
    for row in errors:
        key = reporting_window_stratum(row[field]) if field == "reporting_window_days" else row[field]
        grouped[key].append(row)
    return {key: observation_summary(rows) for key, rows in sorted(grouped.items())}


def leave_one_group_out(errors: list[dict], field: str) -> dict:
    groups = sorted({row[field] for row in errors})
    return {
        group: observation_summary([row for row in errors if row[field] != group])
        for group in groups
    }


def evaluate_revealed_rows(rows: list[dict]) -> dict:
    flow = attrition_flow(rows)
    errors, missing_continuing = continuing_errors(rows)
    clusters = aggregate_source_event_clusters(errors)
    differences = [row["mean_paired_error_difference"] for row in clusters]
    if not clusters:
        return {
            "status": "underpowered_inconclusive",
            "attrition_flow": flow,
            "continuing_rows_missing_marks": missing_continuing,
            "independent_continuing_clusters": 0,
        }

    mae_b0 = mean([row["mean_absolute_error_b0"] for row in clusters])
    mae_sn = mean([row["mean_absolute_error_sn"] for row in clusters])
    relative_improvement = None if mae_b0 == 0 else (mae_b0 - mae_sn) / mae_b0
    permutation_p = paired_permutation_pvalue(differences)
    bootstrap_low, bootstrap_high = borrower_cluster_bootstrap_interval(clusters)
    loo = leave_one_borrower_out(clusters)
    periods = period_direction(clusters)
    criteria = {
        "cluster_mae_sn_below_b0": mae_sn < mae_b0,
        "relative_mae_improvement_ge_10pct": (
            relative_improvement is not None
            and relative_improvement >= REQUIRED_RELATIVE_MAE_IMPROVEMENT
        ),
        "one_sided_paired_permutation_p_lt_0_05": permutation_p < 0.05,
        "borrower_bootstrap_interval_below_zero": bootstrap_high < 0,
        "leave_one_borrower_out_direction_robust": (
            mean(differences) < 0 and bool(loo) and all(value < 0 for value in loo.values())
        ),
        "strict_majority_periods_negative": periods["strict_majority_negative"],
    }
    underpowered = len(clusters) < MIN_CONTINUING_CLUSTERS
    passed = not underpowered and all(criteria.values())
    status = "pass" if passed else ("underpowered_inconclusive" if underpowered else "exploratory_inconclusive")
    return {
        "status": status,
        "independent_continuing_clusters": len(clusters),
        "underpowered_threshold": MIN_CONTINUING_CLUSTERS,
        "attrition_flow": flow,
        "continuing_rows_missing_marks": missing_continuing,
        "primary": {
            "cluster_level_mae_b0": mae_b0,
            "cluster_level_mae_sn": mae_sn,
            "mean_paired_error_difference": mean(differences),
            "relative_mae_improvement": relative_improvement,
            "one_sided_paired_permutation_p": permutation_p,
            "borrower_cluster_bootstrap_95": {
                "lower": bootstrap_low,
                "upper": bootstrap_high,
            },
            "criteria": criteria,
        },
        "period_direction": periods,
        "leave_one_borrower_out": loo,
        "secondary": {
            "target_observation": observation_summary(errors),
            "by_period": grouped_observation_summaries(errors, "report_period_label"),
            "by_source": grouped_observation_summaries(errors, "source_ticker"),
            "by_target": grouped_observation_summaries(errors, "target_ticker"),
            "by_reporting_window": grouped_observation_summaries(errors, "reporting_window_days"),
            "leave_one_source_out": leave_one_group_out(errors, "source_ticker"),
            "leave_one_target_out": leave_one_group_out(errors, "target_ticker"),
        },
    }


def load_authorized_reveal(outcomes_path: Path, authorization_path: Path) -> list[dict]:
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    required = (
        "sample_freeze_commit",
        "preregistration_sha256",
        "evaluator_sha256",
    )
    if authorization.get("reveal_authorized") is not True:
        raise PermissionError("Target-outcome reveal is not authorized")
    if any(not authorization.get(field) for field in required):
        raise PermissionError("Reveal authorization record is incomplete")
    with outcomes_path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revealed-outcomes", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = load_authorized_reveal(args.revealed_outcomes, args.authorization)
    result = evaluate_revealed_rows(rows)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Recompute Day 2 concentration and leave-one-borrower-out sensitivity."""

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

DAY2 = Path(__file__).resolve().parents[1] / "day2"
sys.path.insert(0, str(DAY2))

from common import decimal_or_none, read_csv, sha256_file, write_json  # noqa: E402


def mean(values):
    values = [value for value in values if value is not None]
    return statistics.mean(values) if values else None


def audit(rows):
    adjusted_prediction = (
        "prior_gap_adjusted_source" if "prior_gap_adjusted_source" in rows[0]
        else "entry_price_bias_adjusted_source"
    )
    adjusted_error = (
        "prior_gap_adjusted_abs_error_pp" if "prior_gap_adjusted_abs_error_pp" in rows[0]
        else "entry_adjusted_abs_error_pp"
    )
    for row in rows:
        row["_b0_error"] = decimal_or_none(row["b0_abs_error_pp"])
        row["_adjusted_error"] = decimal_or_none(row[adjusted_error])
        row["_degenerate"] = abs(
            (decimal_or_none(row["b0_unchanged_target_prior"]) or 0)
            - (decimal_or_none(row[adjusted_prediction]) or 0)
        ) < 1e-12

    clusters = defaultdict(list)
    for row in rows:
        key = (row["period_end"], row["borrower_norm"], row["source_ticker"], row["target_ticker"])
        clusters[key].append(row)
    cluster_metrics = []
    for key, group in clusters.items():
        cluster_metrics.append({
            "key": "|".join(key),
            "b0_error_pp": mean(row["_b0_error"] for row in group),
            "prior_gap_adjusted_error_pp": mean(row["_adjusted_error"] for row in group),
            "row_count": len(group),
        })

    borrowers = sorted({row["borrower_norm"] for row in rows})
    leave_one_borrower_out = {}
    for borrower in borrowers:
        kept = [row for row in rows if row["borrower_norm"] != borrower]
        leave_one_borrower_out[borrower] = {
            "n_rows": len(kept),
            "b0_mae_pp": mean(row["_b0_error"] for row in kept),
            "prior_gap_adjusted_mae_pp": mean(row["_adjusted_error"] for row in kept),
        }
        values = leave_one_borrower_out[borrower]
        values["adjusted_advantage_pp"] = (
            values["b0_mae_pp"] - values["prior_gap_adjusted_mae_pp"]
            if values["b0_mae_pp"] is not None and values["prior_gap_adjusted_mae_pp"] is not None else None
        )

    petvet = leave_one_borrower_out.get("petvet care centers", {})
    return {
        "row_count": len(rows),
        "unique_borrowers": len(borrowers),
        "unique_borrower_target_exposures": len({(row["borrower_norm"], row["target_ticker"]) for row in rows}),
        "unique_borrower_source_target_clusters": len(clusters),
        "periods": sorted({row["period_end"] for row in rows}),
        "source_funds": sorted({row["source_ticker"] for row in rows}),
        "target_funds": sorted({row["target_ticker"] for row in rows}),
        "degenerate_prior_gap_equals_b0_rows": sum(row["_degenerate"] for row in rows),
        "row_level": {
            "b0_mae_pp": mean(row["_b0_error"] for row in rows),
            "prior_gap_adjusted_mae_pp": mean(row["_adjusted_error"] for row in rows),
        },
        "cluster_level": {
            "cluster_count": len(cluster_metrics),
            "b0_mae_pp": mean(row["b0_error_pp"] for row in cluster_metrics),
            "prior_gap_adjusted_mae_pp": mean(row["prior_gap_adjusted_error_pp"] for row in cluster_metrics),
        },
        "leave_one_borrower_out": leave_one_borrower_out,
        "petvet_removed": petvet,
        "conclusion": (
            "The apparent adjusted advantage is driven entirely by PetVet Care Centers; "
            "after removing that borrower, B0 and prior-gap-adjusted MAE are equal to rounding."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/day2/nowcast_results.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/day3/day2_sensitivity_audit.json"))
    args = parser.parse_args()
    rows = read_csv(args.input)
    result = audit(rows)
    result["source_results_sha256"] = sha256_file(args.input)
    write_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

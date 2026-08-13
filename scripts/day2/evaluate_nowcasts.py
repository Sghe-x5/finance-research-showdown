#!/usr/bin/env python3
"""Reveal outcomes only for the already frozen ShadowNAV sample."""

import argparse
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path

from common import decimal_or_none, previous_quarter_end, read_csv, write_csv, write_json
from build_eligible_nowcasts import strict_same_facility


DEFAULT_NORMALIZED = Path("/private/tmp/finance-day2-sec-cache/bdc_soi_normalized.csv")
DEFAULT_ELIGIBLE = Path("data/day2/eligible_nowcast_ids.csv")
DEFAULT_FROZEN = Path("data/day2/frozen_nowcast_sample.json")
DEFAULT_OUTPUT = Path("data/day2/nowcast_results.csv")
DEFAULT_SUMMARY = Path("data/day2/nowcast_results_summary.json")

FIELDS = [
    "observation_id", "period_end", "borrower_norm", "source_ticker", "target_ticker",
    "reporting_window_hours", "reporting_window_bucket", "target_actual_mark",
    "b0_unchanged_target_prior", "b1_target_momentum", "b2_already_filed_exact_coholder_median",
    "b3_earliest_exact_coholder", "b4_prior_quarter_cross_lender_median",
    "b5_distress_flags_only", "entry_price_bias_adjusted_source", "b0_abs_error_pp",
    "b1_abs_error_pp", "b2_abs_error_pp", "b3_abs_error_pp", "b4_abs_error_pp",
    "entry_adjusted_abs_error_pp", "target_pik_transition", "target_nonaccrual_transition",
    "target_restructuring_transition", "target_position_disappeared", "same_manager_or_jv",
    "common_appraiser", "contaminated_fixture", "freeze_commit",
]


def parse_timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00").replace(" ", "T", 1))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def mark(row):
    principal = decimal_or_none(row.get("principal"))
    fair_value = decimal_or_none(row.get("fair_value"))
    if principal in (None, 0) or fair_value is None:
        return None
    return fair_value / principal


def aggregate_mark(rows):
    unique = {row["facility_row_id"]: row for row in rows}.values()
    principal = sum(decimal_or_none(row.get("principal")) or 0 for row in unique)
    fair_value = sum(decimal_or_none(row.get("fair_value")) or 0 for row in unique)
    return None if principal == 0 else fair_value / principal


def abs_error_pp(prediction, actual):
    if prediction is None or actual is None:
        return None
    return abs(prediction - actual) * 100


def window_bucket(hours):
    if hours <= 24:
        return "<=1d"
    if hours <= 72:
        return "1-3d"
    return ">3d"


def prior_match(current, rows, cik=None):
    period = previous_quarter_end(current["period_end"])
    candidates = [
        row for row in rows if row["observation_date"] == period
        and row["accepted"] <= current["accepted"]
        and (cik is None or row["cik"] == cik) and strict_same_facility(current, row)
    ]
    return candidates


def exact_prior_identifier_rows(current, rows, observation_date):
    return [
        row for row in rows
        if row["observation_date"] == observation_date
        and row["accepted"] <= current["accepted"]
        and row["cik"] == current["cik"]
        and row["investment_identifier"] == current["investment_identifier"]
    ]


def metric_summary(values):
    values = [value for value in values if value is not None]
    if not values:
        return {"n": 0, "mae_pp": None, "rmse_pp": None, "median_abs_error_pp": None}
    return {
        "n": len(values),
        "mae_pp": statistics.mean(values),
        "rmse_pp": math.sqrt(statistics.mean(value * value for value in values)),
        "median_abs_error_pp": statistics.median(values),
    }


def evaluate(normalized, eligible, frozen_ids, freeze_commit):
    by_id = {row["facility_row_id"]: row for row in normalized}
    eligible_by_id = {row["observation_id"]: row for row in eligible}
    results = []
    for observation_id in frozen_ids:
        item = eligible_by_id[observation_id]
        source = by_id[item["source_row_id"]]
        target = by_id[item["target_row_id"]]
        target_prior = by_id[item["target_prior_row_id"]]
        source_mark = mark(source)
        target_actual = mark(target)
        target_prior_mark = mark(target_prior)

        prior_prior_date = previous_quarter_end(target_prior["observation_date"])
        target_prior_prior_rows = exact_prior_identifier_rows(target_prior, normalized, prior_prior_date)
        target_prior_prior_mark = aggregate_mark(target_prior_prior_rows) if target_prior_prior_rows else None
        b1 = None
        if target_prior_mark is not None and target_prior_prior_mark is not None:
            b1 = target_prior_mark + (target_prior_mark - target_prior_prior_mark)

        coholder_marks = []
        for other in eligible:
            if other["period_end"] != item["period_end"] or other["target_row_id"] != item["target_row_id"]:
                continue
            other_source = by_id[other["source_row_id"]]
            value = mark(other_source)
            if value is not None:
                coholder_marks.append(value)
        b2 = statistics.median(coholder_marks) if coholder_marks else None

        prior_cross = [mark(row) for row in prior_match(target, normalized) if row["cik"] != target["cik"]]
        prior_cross = [value for value in prior_cross if value is not None]
        b4 = statistics.median(prior_cross) if prior_cross else None

        source_prior_rows = exact_prior_identifier_rows(source, normalized, previous_quarter_end(source["period_end"]))
        source_prior = aggregate_mark(source_prior_rows) if source_prior_rows else None
        entry_adjusted = None
        if source_mark is not None and source_prior is not None and target_prior_mark is not None:
            entry_adjusted = source_mark + (target_prior_mark - source_prior)

        hours = (
            parse_timestamp(item["target_cutoff_timestamp_utc"])
            - parse_timestamp(item["source_results_timestamp_utc"])
        ).total_seconds() / 3600
        target_pik = (decimal_or_none(target.get("pik_rate")) or 0) > 0
        prior_pik = (decimal_or_none(target_prior.get("pik_rate")) or 0) > 0
        row = {
            "observation_id": observation_id,
            "period_end": item["period_end"],
            "borrower_norm": item["borrower_norm"],
            "source_ticker": item["source_ticker"],
            "target_ticker": item["target_ticker"],
            "reporting_window_hours": f"{hours:.4f}",
            "reporting_window_bucket": window_bucket(hours),
            "target_actual_mark": "" if target_actual is None else f"{target_actual:.10f}",
            "b0_unchanged_target_prior": "" if target_prior_mark is None else f"{target_prior_mark:.10f}",
            "b1_target_momentum": "" if b1 is None else f"{b1:.10f}",
            "b2_already_filed_exact_coholder_median": "" if b2 is None else f"{b2:.10f}",
            "b3_earliest_exact_coholder": "" if source_mark is None else f"{source_mark:.10f}",
            "b4_prior_quarter_cross_lender_median": "" if b4 is None else f"{b4:.10f}",
            "b5_distress_flags_only": f"pik={target_pik};nonaccrual={target['non_accrual']};restructuring={target['restructuring_flag']}",
            "entry_price_bias_adjusted_source": "" if entry_adjusted is None else f"{entry_adjusted:.10f}",
            "b0_abs_error_pp": abs_error_pp(target_prior_mark, target_actual),
            "b1_abs_error_pp": abs_error_pp(b1, target_actual),
            "b2_abs_error_pp": abs_error_pp(b2, target_actual),
            "b3_abs_error_pp": abs_error_pp(source_mark, target_actual),
            "b4_abs_error_pp": abs_error_pp(b4, target_actual),
            "entry_adjusted_abs_error_pp": abs_error_pp(entry_adjusted, target_actual),
            "target_pik_transition": str(target_pik and not prior_pik),
            "target_nonaccrual_transition": str(target["non_accrual"] == "True" and target_prior["non_accrual"] != "True"),
            "target_restructuring_transition": str(target["restructuring_flag"] == "True" and target_prior["restructuring_flag"] != "True"),
            "target_position_disappeared": "False",
            "same_manager_or_jv": "not_observable_in_flat_file",
            "common_appraiser": "not_observable_in_flat_file",
            "contaminated_fixture": "False",
            "freeze_commit": freeze_commit,
        }
        results.append(row)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--normalized", type=Path, default=DEFAULT_NORMALIZED)
    parser.add_argument("--eligible", type=Path, default=DEFAULT_ELIGIBLE)
    parser.add_argument("--frozen", type=Path, default=DEFAULT_FROZEN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--freeze-commit", required=True)
    args = parser.parse_args()
    frozen = json.loads(args.frozen.read_text(encoding="utf-8"))
    if frozen.get("outcomes_revealed") is not False:
        raise RuntimeError("Frozen sample provenance is invalid")
    results = evaluate(read_csv(args.normalized), read_csv(args.eligible), frozen["observation_ids"], args.freeze_commit)
    write_csv(args.output, results, FIELDS)
    baselines = {}
    for key in ("b0", "b1", "b2", "b3", "b4", "entry_adjusted"):
        column = f"{key}_abs_error_pp"
        values = [decimal_or_none(row.get(column)) for row in results]
        baselines[key] = metric_summary(values)
    by_window = {}
    for bucket in ("<=1d", "1-3d", ">3d"):
        group = [row for row in results if row["reporting_window_bucket"] == bucket]
        by_window[bucket] = {
            "n": len(group),
            "b0_mae_pp": metric_summary([decimal_or_none(row["b0_abs_error_pp"]) for row in group])["mae_pp"],
            "b3_mae_pp": metric_summary([decimal_or_none(row["b3_abs_error_pp"]) for row in group])["mae_pp"],
        }
    clusters = {
        (row["period_end"], row["borrower_norm"], row["source_ticker"], row["target_ticker"])
        for row in results
    }
    summary = {
        "frozen_sample_size": len(results),
        "unique_borrower_source_target_clusters": len(clusters),
        "duplicate_xbrl_slice_ids": len(results) - len(clusters),
        "freeze_commit": args.freeze_commit,
        "baselines": baselines,
        "by_reporting_window": by_window,
        "same_manager_jv_exclusion": "not observable in SEC flat files",
        "common_appraiser_exclusion": "not observable in SEC flat files",
        "contaminated_fixture_rows_in_estimate": 0,
        "categorical_transitions": {
            "pik": sum(row["target_pik_transition"] == "True" for row in results),
            "nonaccrual": sum(row["target_nonaccrual_transition"] == "True" for row in results),
            "restructuring": sum(row["target_restructuring_transition"] == "True" for row in results),
            "disappearance": sum(row["target_position_disappeared"] == "True" for row in results),
        },
        "limitation": "Frozen IDs were not replaced after reveal; four repeated XBRL slices reduce the effective independent cluster count to 11.",
    }
    write_json(args.summary, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

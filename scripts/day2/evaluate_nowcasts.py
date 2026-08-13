#!/usr/bin/env python3
"""Reveal outcomes for a hash-locked aggregated ShadowNAV sample."""

import argparse
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from common import decimal_or_none, previous_quarter_end, read_csv, sha256_file, write_csv, write_json
from build_eligible_nowcasts import strict_same_facility


DEFAULT_FACILITIES = Path("/private/tmp/finance-day3-sec-cache/bdc_facilities_agg.csv")
DEFAULT_ELIGIBLE = Path("data/day3/eligible_prefreeze_ids.csv")
DEFAULT_FROZEN = Path("data/day3/frozen_nowcast_sample.json")
DEFAULT_OUTPUT = Path("data/day3/nowcast_results.csv")
DEFAULT_SUMMARY = Path("data/day3/nowcast_results_summary.json")

FIELDS = [
    "observation_id", "period_end", "borrower_norm", "source_ticker", "target_ticker",
    "source_information_timestamp_utc", "target_cutoff_timestamp_utc",
    "reporting_window_hours", "reporting_window_bucket", "target_actual_mark",
    "b0_unchanged_target_prior", "b1_target_momentum",
    "b2_already_filed_exact_coholder_median", "b3_earliest_exact_coholder",
    "b4_previous_quarter_cross_lender_median", "b5_distress_flags_only",
    "prior_gap_adjusted_source", "b0_abs_error_pp", "b1_abs_error_pp",
    "b2_abs_error_pp", "b3_abs_error_pp", "b4_abs_error_pp",
    "prior_gap_adjusted_abs_error_pp", "target_pik_transition",
    "target_nonaccrual_transition", "target_restructuring_transition",
    "target_position_disappeared", "target_current_match_count", "same_manager_or_jv",
    "common_appraiser", "contaminated_fixture", "freeze_commit",
    "evaluation_script_sha256",
]


def parse_timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00").replace(" ", "T", 1))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def mark(row):
    direct = decimal_or_none(row.get("mark_fv_to_principal"))
    if direct is not None:
        return direct
    principal = decimal_or_none(row.get("principal"))
    fair_value = decimal_or_none(row.get("fair_value"))
    if principal in (None, 0) or fair_value is None:
        return None
    return fair_value / principal


def aggregate_mark(rows):
    """Compatibility helper; aggregated input should normally contain one row."""
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


def verify_frozen_evaluator(frozen, evaluator_path):
    """Refuse a reveal when the evaluator differs from the frozen artifact."""
    current_sha256 = sha256_file(evaluator_path)
    frozen_sha256 = frozen.get("evaluation_script_sha256")
    if frozen_sha256 != current_sha256:
        raise RuntimeError(
            "Evaluator changed after freeze: "
            f"frozen={frozen_sha256} current={current_sha256}"
        )
    return current_sha256


def facility_indexes(facilities):
    by_id = {row["economic_facility_id"]: row for row in facilities}
    by_period_ticker_borrower = defaultdict(list)
    for row in facilities:
        if row["is_current_period"] == "True":
            by_period_ticker_borrower[(row["period_end"], row["ticker"], row["borrower_norm"])].append(row)
    return by_id, by_period_ticker_borrower


def exact_options(reference, options):
    return [row for row in options if strict_same_facility(reference, row)]


def one_fund_one_mark(observations, by_id):
    earliest_by_source = {}
    for item in observations:
        current = earliest_by_source.get(item["source_ticker"])
        if current is None or parse_timestamp(item["source_information_timestamp_utc"]) < parse_timestamp(current["source_information_timestamp_utc"]):
            earliest_by_source[item["source_ticker"]] = item
    values = []
    for item in earliest_by_source.values():
        value = mark(by_id[item["source_facility_id"]])
        if value is not None:
            values.append((item["source_ticker"], item["source_information_timestamp_utc"], value))
    return sorted(values, key=lambda item: (parse_timestamp(item[1]), item[0]))


def evaluate(facilities, eligible, frozen_ids, freeze_commit, evaluator_sha256):
    by_id, by_period_ticker_borrower = facility_indexes(facilities)
    eligible_by_id = {row["observation_id"]: row for row in eligible}
    grouped = defaultdict(list)
    for row in eligible:
        grouped[(row["period_end"], row["target_ticker"], row["target_prior_facility_id"])].append(row)

    results = []
    for observation_id in frozen_ids:
        item = eligible_by_id[observation_id]
        source = by_id[item["source_facility_id"]]
        source_prior = by_id[item["source_prior_facility_id"]]
        target_prior = by_id[item["target_prior_facility_id"]]
        source_mark = mark(source)
        source_prior_mark = mark(source_prior)
        target_prior_mark = mark(target_prior)

        current_options = by_period_ticker_borrower.get(
            (item["period_end"], item["target_ticker"], item["borrower_norm"]), []
        )
        target_matches = exact_options(target_prior, current_options)
        target_current = target_matches[0] if len(target_matches) == 1 else None
        disappeared = len(target_matches) == 0
        target_actual = mark(target_current) if target_current else None

        prior_prior_period = previous_quarter_end(target_prior["period_end"])
        prior_prior_options = by_period_ticker_borrower.get(
            (prior_prior_period, item["target_ticker"], item["borrower_norm"]), []
        )
        prior_prior_matches = exact_options(target_prior, prior_prior_options)
        target_prior_prior_mark = mark(prior_prior_matches[0]) if len(prior_prior_matches) == 1 else None
        b1 = None
        if target_prior_mark is not None and target_prior_prior_mark is not None:
            b1 = target_prior_mark + (target_prior_mark - target_prior_prior_mark)

        coholders = one_fund_one_mark(
            grouped[(item["period_end"], item["target_ticker"], item["target_prior_facility_id"])], by_id
        )
        b2 = statistics.median(value for _, _, value in coholders) if coholders else None
        b3 = coholders[0][2] if coholders else None

        prior_lender_marks = {}
        for (period, ticker, borrower), options in by_period_ticker_borrower.items():
            if period != target_prior["period_end"] or borrower != item["borrower_norm"] or ticker == item["target_ticker"]:
                continue
            matches = exact_options(target_prior, options)
            if len(matches) == 1 and mark(matches[0]) is not None:
                prior_lender_marks[ticker] = mark(matches[0])
        b4 = statistics.median(prior_lender_marks.values()) if prior_lender_marks else None

        prior_gap = None
        if source_mark is not None and source_prior_mark is not None and target_prior_mark is not None:
            prior_gap = target_prior_mark + (source_mark - source_prior_mark)

        hours = (
            parse_timestamp(item["target_cutoff_timestamp_utc"])
            - parse_timestamp(item["source_information_timestamp_utc"])
        ).total_seconds() / 3600
        target_pik = bool(target_current and (decimal_or_none(target_current.get("pik_rate")) or 0) > 0)
        prior_pik = (decimal_or_none(target_prior.get("pik_rate")) or 0) > 0
        row = {
            "observation_id": observation_id,
            "period_end": item["period_end"],
            "borrower_norm": item["borrower_norm"],
            "source_ticker": item["source_ticker"],
            "target_ticker": item["target_ticker"],
            "source_information_timestamp_utc": item["source_information_timestamp_utc"],
            "target_cutoff_timestamp_utc": item["target_cutoff_timestamp_utc"],
            "reporting_window_hours": f"{hours:.4f}",
            "reporting_window_bucket": window_bucket(hours),
            "target_actual_mark": "" if target_actual is None else f"{target_actual:.10f}",
            "b0_unchanged_target_prior": "" if target_prior_mark is None else f"{target_prior_mark:.10f}",
            "b1_target_momentum": "" if b1 is None else f"{b1:.10f}",
            "b2_already_filed_exact_coholder_median": "" if b2 is None else f"{b2:.10f}",
            "b3_earliest_exact_coholder": "" if b3 is None else f"{b3:.10f}",
            "b4_previous_quarter_cross_lender_median": "" if b4 is None else f"{b4:.10f}",
            "b5_distress_flags_only": (
                "disappeared=True" if disappeared else
                f"pik={target_pik};nonaccrual={target_current['non_accrual']};restructuring={target_current['restructuring_flag']}"
            ),
            "prior_gap_adjusted_source": "" if prior_gap is None else f"{prior_gap:.10f}",
            "b0_abs_error_pp": abs_error_pp(target_prior_mark, target_actual),
            "b1_abs_error_pp": abs_error_pp(b1, target_actual),
            "b2_abs_error_pp": abs_error_pp(b2, target_actual),
            "b3_abs_error_pp": abs_error_pp(b3, target_actual),
            "b4_abs_error_pp": abs_error_pp(b4, target_actual),
            "prior_gap_adjusted_abs_error_pp": abs_error_pp(prior_gap, target_actual),
            "target_pik_transition": str(bool(target_current) and target_pik and not prior_pik),
            "target_nonaccrual_transition": str(bool(target_current) and target_current["non_accrual"] == "True" and target_prior["non_accrual"] != "True"),
            "target_restructuring_transition": str(bool(target_current) and target_current["restructuring_flag"] == "True" and target_prior["restructuring_flag"] != "True"),
            "target_position_disappeared": str(disappeared),
            "target_current_match_count": len(target_matches),
            "same_manager_or_jv": "not_observable_in_flat_file",
            "common_appraiser": "not_observable_in_flat_file",
            "contaminated_fixture": "False",
            "freeze_commit": freeze_commit,
            "evaluation_script_sha256": evaluator_sha256,
        }
        results.append(row)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--facilities", type=Path, default=DEFAULT_FACILITIES)
    parser.add_argument("--eligible", type=Path, default=DEFAULT_ELIGIBLE)
    parser.add_argument("--frozen", type=Path, default=DEFAULT_FROZEN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--freeze-commit", required=True)
    args = parser.parse_args()
    frozen = json.loads(args.frozen.read_text(encoding="utf-8"))
    evaluator_sha256 = verify_frozen_evaluator(frozen, Path(__file__))
    if frozen.get("outcomes_revealed") is not False:
        raise RuntimeError("Frozen sample provenance is invalid")
    results = evaluate(
        read_csv(args.facilities), read_csv(args.eligible), frozen["observation_ids"],
        args.freeze_commit, evaluator_sha256,
    )
    write_csv(args.output, results, FIELDS)
    baselines = {}
    columns = {
        "b0": "b0_abs_error_pp", "b1": "b1_abs_error_pp", "b2": "b2_abs_error_pp",
        "b3": "b3_abs_error_pp", "b4": "b4_abs_error_pp",
        "prior_gap_adjusted": "prior_gap_adjusted_abs_error_pp",
    }
    for key, column in columns.items():
        baselines[key] = metric_summary([decimal_or_none(row.get(column)) for row in results])
    summary = {
        "frozen_sample_size": len(results),
        "freeze_commit": args.freeze_commit,
        "evaluation_script_sha256": evaluator_sha256,
        "baselines": baselines,
        "disappearance_count": sum(row["target_position_disappeared"] == "True" for row in results),
        "ambiguous_target_current_matches": sum(int(row["target_current_match_count"]) > 1 for row in results),
        "contaminated_fixture_rows_in_estimate": 0,
        "one_source_fund_one_vote": True,
        "unit_of_analysis": "BDC x quarter_end x borrower x economic_facility",
    }
    write_json(args.summary, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Count pre-reveal eligible source movements without revealing target outcomes."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

DAY2 = Path(__file__).resolve().parents[1] / "day2"
sys.path.insert(0, str(DAY2))

from build_eligible_nowcasts import build_eligible  # noqa: E402
from common import decimal_or_none, read_csv, sha256_file, write_json  # noqa: E402


DEFAULT_INPUT = Path("/private/tmp/finance-day3-sec-cache/bdc_facilities_agg.csv")
DEFAULT_REPORTING = Path("02_showdown/reporting_order.csv")
DEFAULT_OUTPUT = Path("data/day3/movement_power_guard.json")
DEVELOPMENT_QUARTER = "2025Q3"
THRESHOLD_PP = 0.5


def mark(row):
    direct = decimal_or_none(row.get("mark_fv_to_principal"))
    if direct is not None:
        return direct
    principal = decimal_or_none(row.get("principal"))
    fair_value = decimal_or_none(row.get("fair_value"))
    return None if principal in (None, 0) or fair_value is None else fair_value / principal


def count_movements(rows, reporting_rows, threshold_pp=THRESHOLD_PP):
    """Count unique eligible source facilities; target current rows are never read."""
    eligible = build_eligible(rows, reporting_rows)
    by_id = {row["economic_facility_id"]: row for row in rows}
    by_period = {}
    for quarter in sorted({row["quarter"] for row in eligible}):
        quarter_rows = [row for row in eligible if row["quarter"] == quarter]
        valid = []
        for observation in quarter_rows:
            current_mark = mark(by_id[observation["source_facility_id"]])
            prior_mark = mark(by_id[observation["source_prior_facility_id"]])
            if current_mark is None or prior_mark is None:
                continue
            valid.append((observation, (current_mark - prior_mark) * 100))
        movements = [(row, delta) for row, delta in valid if abs(delta) >= threshold_pp]
        unique_sources = {
            (row["source_ticker"], row["source_facility_id"]): row for row, _ in movements
        }
        by_period[quarter] = {
            "period_end": quarter_rows[0]["period_end"],
            "classification": "development" if quarter == DEVELOPMENT_QUARTER else "untouched_target_outcome_period",
            "eligible_pre_reveal_observations": len(quarter_rows),
            "eligible_observations_with_source_delta": len(valid),
            "movement_eligible_observations": len(movements),
            "movement_source_facility_events": len(unique_sources),
            "movement_unique_borrowers": len({row["borrower_norm"] for row in unique_sources.values()}),
            "movement_by_source_ticker": dict(sorted(Counter(row["source_ticker"] for row in unique_sources.values()).items())),
        }
    return by_period


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--reporting-order", type=Path, default=DEFAULT_REPORTING)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--threshold-pp", type=float, default=THRESHOLD_PP)
    args = parser.parse_args()
    by_period = count_movements(read_csv(args.input), read_csv(args.reporting_order), args.threshold_pp)
    untouched = [value for value in by_period.values() if value["classification"].startswith("untouched")]
    movement_total = sum(item["movement_source_facility_events"] for item in untouched)
    output = {
        "aggregated_input_sha256": sha256_file(args.input),
        "reporting_order_sha256": sha256_file(args.reporting_order),
        "unit": "unique source BDC x quarter_end x borrower x economic_facility among pre-reveal eligible source-target observations",
        "movement_definition": f"absolute aggregated facility mark change >= {args.threshold_pp:.1f} percentage points",
        "development_quarter_excluded_from_power_guard": DEVELOPMENT_QUARTER,
        "periods": by_period,
        "untouched_movement_source_facility_events_total": movement_total,
        "untouched_period_unique_borrower_counts_sum_not_deduplicated_across_time": sum(item["movement_unique_borrowers"] for item in untouched),
        "power_guard_minimum": 20,
        "power_guard_passed_for_planning": movement_total >= 20,
        "required_action_if_failed": "Do not plan a reveal; expand the fund/reporting-order universe first.",
        "target_outcomes_revealed_by_this_script": False,
        "note": "Eligibility uses source current, source prior and target prior only. It never reads target same-quarter facilities.",
    }
    write_json(args.output, output)
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

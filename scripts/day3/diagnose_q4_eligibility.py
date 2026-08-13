#!/usr/bin/env python3
"""Explain why the Day 2 SEC inputs contain no 2025Q4 nowcast candidates."""

import argparse
import json
from collections import Counter
from pathlib import Path

import sys

DAY2 = Path(__file__).resolve().parents[1] / "day2"
sys.path.insert(0, str(DAY2))

from common import read_csv, write_json  # noqa: E402


def diagnose(normalized_rows, candidates, eligible, reporting):
    current = [row for row in normalized_rows if row["is_current_period"] == "True"]
    archive_periods = {}
    for row in current:
        archive_periods.setdefault(row["archive_id"], Counter())[row["period_end"]] += 1
    accepted_year_quarters = Counter()
    for row in current:
        stamp = row["accepted"][:7]
        if len(stamp) == 7:
            year, month = stamp.split("-")
            accepted_year_quarters[f"{year}Q{(int(month) - 1) // 3 + 1}"] += 1

    report_quarters = Counter(row["quarter"] for row in reporting)
    result = {
        "day2_archive_current_position_periods": {
            archive: dict(sorted(counts.items())) for archive, counts in sorted(archive_periods.items())
        },
        "accepted_calendar_quarters": dict(sorted(accepted_year_quarters.items())),
        "candidate_position_periods": dict(sorted(Counter(row["period_end"] for row in candidates).items())),
        "eligible_result_quarters": dict(sorted(Counter(row["quarter"] for row in eligible).items())),
        "reporting_order_quarters": dict(sorted(report_quarters.items())),
        "q4_mapping_bug": False,
        "root_cause": (
            "SEC BDC archive labels are filing-acceptance quarters, not investment position quarter ends. "
            "The 2025q4 archive contains filings accepted in 2025Q4 for positions through 2025-09-30. "
            "Positions at 2025-12-31 are filed in 2026Q1 and require a 2026q1 BDC archive, which was not "
            "linked by the official SEC index during Day 2. Therefore the Day 2 parser correctly produced "
            "2025Q3 positions and zero 2025Q4 eligible nowcasts; downloading 2025q4 did not provide Q4 positions."
        ),
        "required_fix": (
            "Name archive periods as acceptance quarters in manifests and derive result quarter only from the "
            "SOI/submission period_end. Do not claim 2025Q4 coverage until an official archive containing "
            "period_end=2025-12-31 is discovered and checksummed."
        ),
    }
    q4_current = sum(
        count for counts in archive_periods.values() for period, count in counts.items()
        if period == "2025-12-31"
    )
    if q4_current:
        result["q4_mapping_bug"] = True
        result["root_cause"] = "Unexpected: Q4 current-position rows exist; downstream mapping requires investigation."
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--normalized", type=Path, default=Path("/private/tmp/finance-day2-sec-cache/bdc_soi_normalized.csv"))
    parser.add_argument("--candidates", type=Path, default=Path("data/day2/facility_candidates.csv"))
    parser.add_argument("--eligible", type=Path, default=Path("data/day2/eligible_nowcast_ids.csv"))
    parser.add_argument("--reporting", type=Path, default=Path("02_showdown/reporting_order.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/day3/q4_eligibility_diagnosis.json"))
    args = parser.parse_args()
    result = diagnose(
        read_csv(args.normalized), read_csv(args.candidates),
        read_csv(args.eligible), read_csv(args.reporting),
    )
    write_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

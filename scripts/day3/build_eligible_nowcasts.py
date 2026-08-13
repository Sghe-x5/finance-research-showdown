#!/usr/bin/env python3
"""Build pre-reveal nowcast IDs from aggregated facilities only.

Eligibility is based on a source's current public facility and the target's
previously public facility. The target's same-quarter row is deliberately not
read, so survival/disappearance remains an outcome to reveal after freezing.
"""

import argparse
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

DAY2 = Path(__file__).resolve().parents[1] / "day2"
sys.path.insert(0, str(DAY2))

from common import (
    days_apart, decimal_or_none, previous_quarter_end, quarter_label, read_csv,
    stable_id, write_csv,
)


LISTED = {
    "ARCC", "OBDC", "BXSL", "FSK", "GBDC", "MAIN", "HTGC", "TSLX",
    "OCSL", "NMFC", "BBDC", "GSBD", "MFIC", "PSEC", "CGBD",
}
CONTAMINATED_KEYS = {
    ("auctane", "ARCC", "BXSL", "2025Q4"),
    ("medallia", "BXSL", "FSK", "2025Q4"),
}
DEFAULT_FACILITIES = Path("/private/tmp/finance-day3-sec-cache/bdc_facilities_agg.csv")
DEFAULT_REPORTING = Path("02_showdown/reporting_order.csv")
DEFAULT_OUTPUT = Path("data/day3/eligible_prefreeze_ids.csv")

FIELDS = [
    "observation_id", "period_end", "quarter", "borrower_norm", "source_ticker",
    "target_ticker", "source_cik", "target_cik", "source_facility_id",
    "source_prior_facility_id", "target_prior_facility_id",
    "source_results_timestamp_utc", "source_soi_acceptance",
    "source_information_timestamp_utc", "target_cutoff_timestamp_utc",
    "source_public_before_target_cutoff", "target_prior_public_before_source",
    "target_held_previous_filing", "exact_facility_evidence",
    "target_current_outcome_used_for_eligibility", "contaminated_excluded",
    "outcomes_revealed", "unit_of_analysis",
]


def parse_timestamp(value):
    value = (value or "").replace("Z", "+00:00").replace(" ", "T", 1)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def later_timestamp(left, right):
    return left if parse_timestamp(left) >= parse_timestamp(right) else right


def strict_same_facility(left, right):
    if left["borrower_norm"] != right["borrower_norm"]:
        return False
    for field in ("debt_equity", "facility_type", "lien", "currency", "reference_rate", "funded_status"):
        lv, rv = left[field], right[field]
        if lv not in {"", "unknown", "UNKNOWN"} and rv not in {"", "unknown", "UNKNOWN"} and lv != rv:
            return False
    spread_left, spread_right = decimal_or_none(left["spread"]), decimal_or_none(right["spread"])
    if spread_left is not None and spread_right is not None and abs(spread_left - spread_right) > 0.0025:
        return False
    maturity_diff = days_apart(left["maturity"], right["maturity"])
    if maturity_diff is not None and maturity_diff > 45:
        return False
    informative = sum(
        left[field] not in {"", "unknown", "UNKNOWN"} and right[field] not in {"", "unknown", "UNKNOWN"}
        for field in ("debt_equity", "facility_type", "lien", "currency", "reference_rate", "funded_status")
    )
    informative += int(spread_left is not None and spread_right is not None)
    informative += int(maturity_diff is not None)
    return informative >= 3


def reporting_map(rows):
    output = {}
    for row in rows:
        output[(row["ticker"], row["quarter"])] = row["first_results_timestamp_utc"]
    return output


def index_facilities(rows):
    by_period_ticker_borrower = defaultdict(list)
    by_id = {}
    for row in rows:
        by_id[row["economic_facility_id"]] = row
        if row["is_current_period"] == "True":
            by_period_ticker_borrower[(row["period_end"], row["ticker"], row["borrower_norm"])].append(row)
    return by_id, by_period_ticker_borrower


def unique_match(facility, options):
    matches = [row for row in options if strict_same_facility(facility, row)]
    if len(matches) != 1:
        return None
    return matches[0]


def build_eligible(facilities, reporting_rows):
    """Construct IDs without consulting target current-quarter facilities."""
    _, indexed = index_facilities(facilities)
    results = reporting_map(reporting_rows)
    sources = [row for row in facilities if row["is_current_period"] == "True" and row["ticker"] in LISTED]
    eligible = []
    seen = set()
    for source in sources:
        quarter = quarter_label(source["period_end"])
        source_results = results.get((source["ticker"], quarter))
        if not source_results:
            continue
        source_information = later_timestamp(source_results, source["accepted"])
        prior_period = previous_quarter_end(source["period_end"])
        source_prior = unique_match(
            source, indexed.get((prior_period, source["ticker"], source["borrower_norm"]), [])
        )
        if not source_prior:
            continue

        for target_ticker in sorted(LISTED - {source["ticker"]}):
            target_cutoff = results.get((target_ticker, quarter))
            if not target_cutoff or parse_timestamp(source_information) >= parse_timestamp(target_cutoff):
                continue
            target_prior = unique_match(
                source, indexed.get((prior_period, target_ticker, source["borrower_norm"]), [])
            )
            if not target_prior:
                continue
            if parse_timestamp(target_prior["accepted"]) >= parse_timestamp(source_information):
                continue
            contaminated_key = (source["borrower_norm"], source["ticker"], target_ticker, quarter)
            if contaminated_key in CONTAMINATED_KEYS:
                continue
            observation_id = "SN3_" + stable_id(
                source["period_end"], source["economic_facility_id"],
                source_prior["economic_facility_id"], target_prior["economic_facility_id"],
                target_ticker, length=28,
            )
            if observation_id in seen:
                continue
            seen.add(observation_id)
            eligible.append({
                "observation_id": observation_id,
                "period_end": source["period_end"],
                "quarter": quarter,
                "borrower_norm": source["borrower_norm"],
                "source_ticker": source["ticker"],
                "target_ticker": target_ticker,
                "source_cik": source["cik"],
                "target_cik": target_prior["cik"],
                "source_facility_id": source["economic_facility_id"],
                "source_prior_facility_id": source_prior["economic_facility_id"],
                "target_prior_facility_id": target_prior["economic_facility_id"],
                "source_results_timestamp_utc": source_results,
                "source_soi_acceptance": source["accepted"],
                "source_information_timestamp_utc": source_information,
                "target_cutoff_timestamp_utc": target_cutoff,
                "source_public_before_target_cutoff": "True",
                "target_prior_public_before_source": "True",
                "target_held_previous_filing": "True",
                "exact_facility_evidence": "aggregated economic facility; target current row not consulted",
                "target_current_outcome_used_for_eligibility": "False",
                "contaminated_excluded": "True",
                "outcomes_revealed": "False",
                "unit_of_analysis": "BDC x quarter_end x borrower x economic_facility",
            })
    return sorted(eligible, key=lambda row: row["observation_id"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--facilities", type=Path, default=DEFAULT_FACILITIES)
    parser.add_argument("--reporting-order", type=Path, default=DEFAULT_REPORTING)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    eligible = build_eligible(read_csv(args.facilities), read_csv(args.reporting_order))
    if not eligible:
        raise RuntimeError("No pre-reveal nowcasts passed the aggregated eligibility filters")
    write_csv(args.output, eligible, FIELDS)
    print(
        f"eligible_prefreeze_count={len(eligible)} "
        f"periods={sorted({row['period_end'] for row in eligible})}; no target current outcomes read"
    )


if __name__ == "__main__":
    main()

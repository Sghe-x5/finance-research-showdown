#!/usr/bin/env python3
"""Build eligible exact-facility nowcast IDs without exposing target outcomes."""

import argparse
from datetime import datetime, timezone
from pathlib import Path

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
DEFAULT_NORMALIZED = Path("/private/tmp/finance-day2-sec-cache/bdc_soi_normalized.csv")
DEFAULT_CANDIDATES = Path("data/day2/facility_candidates.csv")
DEFAULT_REPORTING = Path("02_showdown/reporting_order.csv")
DEFAULT_OUTPUT = Path("data/day2/eligible_nowcast_ids.csv")

FIELDS = [
    "observation_id", "period_end", "quarter", "borrower_norm", "source_ticker",
    "target_ticker", "source_cik", "target_cik", "source_row_id", "target_row_id",
    "target_prior_row_id", "source_results_timestamp_utc", "target_cutoff_timestamp_utc",
    "source_soi_acceptance", "source_public_before_target_cutoff",
    "target_held_previous_filing", "exact_facility_evidence", "candidate_pair_id",
    "contaminated_excluded", "outcomes_revealed",
]


def parse_timestamp(value):
    value = (value or "").replace("Z", "+00:00")
    value = value.replace(" ", "T", 1)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


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
        if row["ticker"] in LISTED or row["ticker"]:
            output[(row["ticker"], row["quarter"])] = row["first_results_timestamp_utc"]
    return output


def find_prior(target, rows_by_observation_cik):
    prior_period = previous_quarter_end(target["period_end"])
    options = rows_by_observation_cik.get((prior_period, target["cik"]), [])
    matches = [
        row for row in options
        if row["accepted"] <= target["accepted"] and strict_same_facility(target, row)
    ]
    if not matches:
        return None
    return sorted(matches, key=lambda row: row["facility_row_id"])[0]


def build_eligible(normalized_rows, candidate_rows, reporting_rows):
    by_id = {row["facility_row_id"]: row for row in normalized_rows}
    by_observation_cik = {}
    for row in normalized_rows:
        by_observation_cik.setdefault((row["observation_date"], row["cik"]), []).append(row)
    results = reporting_map(reporting_rows)
    eligible = []
    seen = set()
    for pair in candidate_rows:
        if pair["predicted_label"] != "same_facility" or pair["match_confidence"] != "high":
            continue
        left, right = by_id.get(pair["left_row_id"]), by_id.get(pair["right_row_id"])
        if not left or not right or not strict_same_facility(left, right):
            continue
        quarter = quarter_label(left["period_end"])
        left_time = results.get((left["ticker"], quarter))
        right_time = results.get((right["ticker"], quarter))
        if not left_time or not right_time or left_time == right_time:
            continue
        if parse_timestamp(left_time) < parse_timestamp(right_time):
            source, target = left, right
            source_results, target_cutoff = left_time, right_time
        else:
            source, target = right, left
            source_results, target_cutoff = right_time, left_time
        if target["ticker"] not in LISTED:
            continue
        contaminated_key = (target["borrower_norm"], source["ticker"], target["ticker"], quarter)
        if contaminated_key in CONTAMINATED_KEYS:
            continue
        if parse_timestamp(source_results) >= parse_timestamp(target_cutoff):
            continue
        if parse_timestamp(source["accepted"]) >= parse_timestamp(target_cutoff):
            continue
        prior = find_prior(target, by_observation_cik)
        if not prior:
            continue
        observation_id = "SN_" + stable_id(
            left["period_end"], source["facility_row_id"], target["facility_row_id"], prior["facility_row_id"], length=28
        )
        if observation_id in seen:
            continue
        seen.add(observation_id)
        eligible.append({
            "observation_id": observation_id,
            "period_end": left["period_end"],
            "quarter": quarter,
            "borrower_norm": target["borrower_norm"],
            "source_ticker": source["ticker"],
            "target_ticker": target["ticker"],
            "source_cik": source["cik"],
            "target_cik": target["cik"],
            "source_row_id": source["facility_row_id"],
            "target_row_id": target["facility_row_id"],
            "target_prior_row_id": prior["facility_row_id"],
            "source_results_timestamp_utc": source_results,
            "target_cutoff_timestamp_utc": target_cutoff,
            "source_soi_acceptance": source["accepted"],
            "source_public_before_target_cutoff": "True",
            "target_held_previous_filing": "True",
            "exact_facility_evidence": pair["evidence"],
            "candidate_pair_id": pair["pair_id"],
            "contaminated_excluded": "True",
            "outcomes_revealed": "False",
        })
    return sorted(eligible, key=lambda row: row["observation_id"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--normalized", type=Path, default=DEFAULT_NORMALIZED)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--reporting-order", type=Path, default=DEFAULT_REPORTING)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    eligible = build_eligible(read_csv(args.normalized), read_csv(args.candidates), read_csv(args.reporting_order))
    if not eligible:
        raise RuntimeError("No eligible nowcasts passed the preregistered filters")
    write_csv(args.output, eligible, FIELDS)
    print(f"eligible_nowcast_count={len(eligible)} periods={sorted({row['period_end'] for row in eligible})}")


if __name__ == "__main__":
    main()

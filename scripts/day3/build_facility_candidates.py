#!/usr/bin/env python3
"""Build conservative cross-BDC facility candidates without using mark outcomes."""

import argparse
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

DAY2 = Path(__file__).resolve().parents[1] / "day2"
sys.path.insert(0, str(DAY2))

from common import days_apart, decimal_or_none, quarter_label, read_csv, sha256_file, stable_id, write_csv, write_json


DEFAULT_INPUT = Path("/private/tmp/finance-day3-sec-cache/bdc_facilities_agg.csv")
DEFAULT_OUTPUT = Path("/private/tmp/finance-day3-sec-cache/facility_candidates.csv")
DEFAULT_METADATA = Path("data/day3/facility_candidates_metadata.json")

FIELDS = [
    "pair_id", "period_end", "quarter", "left_row_id", "right_row_id",
    "left_ticker", "right_ticker", "left_cik", "right_cik", "left_adsh", "right_adsh",
    "left_accepted", "right_accepted", "left_identifier", "right_identifier",
    "left_borrower_norm", "right_borrower_norm", "left_debt_equity", "right_debt_equity",
    "left_facility_type", "right_facility_type", "left_lien", "right_lien",
    "left_currency", "right_currency", "left_reference_rate", "right_reference_rate",
    "left_spread", "right_spread", "spread_diff", "left_maturity", "right_maturity",
    "maturity_diff_days", "left_funded_status", "right_funded_status",
    "left_acquisition_date", "right_acquisition_date", "borrower_exact", "debt_equity_match",
    "facility_type_match", "lien_match", "currency_match", "reference_rate_match",
    "spread_match_25bp", "maturity_match_45d", "funded_status_match", "hard_conflicts",
    "informative_matches", "predicted_label", "match_confidence", "evidence",
]

GENERIC_BLOCKS = {"other", "various", "investment", "portfolio", "cash", "unknown"}


def known_match(left, right, unknown=("", "unknown", "UNKNOWN")):
    if left in unknown or right in unknown:
        return ""
    return str(left == right)


def compare_pair(left, right):
    spread_left = decimal_or_none(left["spread"])
    spread_right = decimal_or_none(right["spread"])
    spread_diff = None if spread_left is None or spread_right is None else abs(spread_left - spread_right)
    maturity_diff = days_apart(left["maturity"], right["maturity"])
    maturity_month_left = (left.get("maturity") or "")[:7]
    maturity_month_right = (right.get("maturity") or "")[:7]
    maturity_month_match = bool(
        len(maturity_month_left) == 7
        and len(maturity_month_right) == 7
        and maturity_month_left == maturity_month_right
    )
    feature_values = {
        "debt_equity_match": known_match(left["debt_equity"], right["debt_equity"]),
        "facility_type_match": known_match(left["facility_type"], right["facility_type"]),
        "lien_match": known_match(left["lien"], right["lien"]),
        "currency_match": known_match(left["currency"], right["currency"]),
        "reference_rate_match": known_match(left["reference_rate"], right["reference_rate"]),
        "spread_match_25bp": "" if spread_diff is None else str(spread_diff <= 0.0025),
        "maturity_match_45d": (
            str(maturity_diff <= 45) if maturity_diff is not None
            else ("True" if maturity_month_match else "")
        ),
        "funded_status_match": known_match(left["funded_status"], right["funded_status"]),
    }
    conflicts = []
    for name in ("debt_equity_match", "facility_type_match", "lien_match", "currency_match", "reference_rate_match", "funded_status_match"):
        if feature_values[name] == "False":
            conflicts.append(name.replace("_match", ""))
    if spread_diff is not None and spread_diff > 0.01:
        conflicts.append("spread_gt_100bp")
    if maturity_diff is not None and maturity_diff > 120:
        conflicts.append("maturity_gt_120d")
    matches = sum(value == "True" for value in feature_values.values())
    borrower = left["borrower_norm"]
    if borrower in GENERIC_BLOCKS or len(borrower) < 4:
        predicted = "unrelated"
        confidence = "high"
    elif conflicts:
        predicted = "same_borrower_different_facility"
        confidence = "high" if any(item in conflicts for item in ("debt_equity", "facility_type", "lien", "currency")) else "medium"
    elif (
        matches >= 4
        and feature_values["debt_equity_match"] != "False"
        and feature_values["facility_type_match"] != "False"
        and (feature_values["spread_match_25bp"] == "True" or feature_values["maturity_match_45d"] == "True")
    ):
        predicted = "same_facility"
        confidence = "high"
    else:
        predicted = "uncertain"
        confidence = "low"

    evidence = [name for name, value in feature_values.items() if value == "True"]
    evidence.extend(f"conflict:{name}" for name in conflicts)
    pair_id = stable_id(left["period_end"], *sorted((left["facility_row_id"], right["facility_row_id"])))
    return {
        "pair_id": pair_id,
        "period_end": left["period_end"],
        "quarter": quarter_label(left["period_end"]),
        "left_row_id": left["facility_row_id"],
        "right_row_id": right["facility_row_id"],
        "left_ticker": left["ticker"],
        "right_ticker": right["ticker"],
        "left_cik": left["cik"],
        "right_cik": right["cik"],
        "left_adsh": left["adsh"],
        "right_adsh": right["adsh"],
        "left_accepted": left["accepted"],
        "right_accepted": right["accepted"],
        "left_identifier": left["investment_identifier"],
        "right_identifier": right["investment_identifier"],
        "left_borrower_norm": borrower,
        "right_borrower_norm": right["borrower_norm"],
        "left_debt_equity": left["debt_equity"],
        "right_debt_equity": right["debt_equity"],
        "left_facility_type": left["facility_type"],
        "right_facility_type": right["facility_type"],
        "left_lien": left["lien"],
        "right_lien": right["lien"],
        "left_currency": left["currency"],
        "right_currency": right["currency"],
        "left_reference_rate": left["reference_rate"],
        "right_reference_rate": right["reference_rate"],
        "left_spread": left["spread"],
        "right_spread": right["spread"],
        "spread_diff": "" if spread_diff is None else f"{spread_diff:.8f}",
        "left_maturity": left["maturity"],
        "right_maturity": right["maturity"],
        "maturity_diff_days": "" if maturity_diff is None else maturity_diff,
        "left_funded_status": left["funded_status"],
        "right_funded_status": right["funded_status"],
        "left_acquisition_date": left["acquisition_date"],
        "right_acquisition_date": right["acquisition_date"],
        "borrower_exact": "True",
        **feature_values,
        "hard_conflicts": "|".join(conflicts),
        "informative_matches": matches,
        "predicted_label": predicted,
        "match_confidence": confidence,
        "evidence": "|".join(evidence),
    }


def build_candidates(rows):
    current = [row for row in rows if row["is_current_period"] == "True" and row["borrower_norm"]]
    blocks = defaultdict(list)
    for row in current:
        blocks[(row["period_end"], row["borrower_norm"])].append(row)
    output = []
    seen = set()
    for _, block in sorted(blocks.items()):
        for left, right in itertools.combinations(sorted(block, key=lambda row: row["facility_row_id"]), 2):
            if left["cik"] == right["cik"]:
                continue
            pair = compare_pair(left, right)
            if pair["pair_id"] in seen:
                continue
            seen.add(pair["pair_id"])
            output.append(pair)
    return sorted(output, key=lambda row: (row["period_end"], row["pair_id"]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    args = parser.parse_args()
    rows = read_csv(args.input)
    candidates = build_candidates(rows)
    if not candidates:
        raise RuntimeError("Candidate universe is empty")
    write_csv(args.output, candidates, FIELDS)
    counts = defaultdict(int)
    for row in candidates:
        counts[f"{row['predicted_label']}:{row['match_confidence']}"] += 1
    metadata = {
        "candidate_pair_count": len(candidates),
        "input_file_sha256": sha256_file(args.input),
        "input_unit": "BDC x observation_date x borrower x economic_facility",
        "periods": sorted({row["period_end"] for row in candidates}),
        "prediction_counts": dict(sorted(counts.items())),
        "outcome_columns_used": [],
        "note": "Candidate construction uses aggregated economic facilities and excludes principal, cost and fair-value outcomes.",
    }
    write_json(args.metadata, metadata)
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

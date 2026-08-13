#!/usr/bin/env python3
"""Compute extended ShadowNAV pre-reveal power and an explicit eligibility funnel."""

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

DAY2 = Path(__file__).resolve().parents[1] / "day2"
DAY3 = Path(__file__).resolve().parent
sys.path.insert(0, str(DAY2))
sys.path.insert(0, str(DAY3))

from build_eligible_nowcasts import (  # noqa: E402
    later_timestamp, parse_timestamp, strict_same_facility, unique_match,
)
from common import (  # noqa: E402
    decimal_or_none, previous_quarter_end, quarter_label, read_csv, sha256_file,
    stable_id, write_csv, write_json,
)
from export_blind_match_benchmark import SEEN_DEVELOPMENT_BORROWERS  # noqa: E402


DEFAULT_FACILITIES = Path("/private/tmp/finance-day3-sec-cache/bdc_facilities_agg.csv")
DEFAULT_CANDIDATES = Path("/private/tmp/finance-day3-sec-cache/facility_candidates.csv")
DEFAULT_REPORTING = Path("data/day3/reporting_order_extended.csv")
DEFAULT_ELIGIBLE = Path("data/day3/eligible_prefreeze_extended.csv")
DEFAULT_MOVEMENT = Path("data/day3/movement_power_guard_extended.json")
DEFAULT_BOTTLENECK = Path("data/day3/eligibility_bottleneck_by_fund.csv")
DEFAULT_FUNNEL = Path("data/day3/eligibility_funnel_summary.json")

DEVELOPMENT_QUARTER = "2025Q3"
MOVEMENT_THRESHOLD = 0.005
MISSING = {"", "unknown", "UNKNOWN"}
GENERIC_BORROWERS = {"other", "various", "investment", "portfolio", "cash", "unknown"}

ELIGIBLE_FIELDS = [
    "observation_id", "report_period_end", "report_period_label", "borrower_norm",
    "source_ticker", "source_cik", "source_listed_status", "target_ticker", "target_cik",
    "source_facility_id", "source_prior_facility_id", "target_prior_facility_id",
    "source_results_timestamp_utc", "source_mark_public_timestamp_utc",
    "source_information_timestamp_utc", "source_mark_public_evidence",
    "target_prior_public_timestamp_utc", "target_cutoff_timestamp_utc",
    "reporting_window_days", "source_current_mark", "source_prior_mark",
    "source_delta_mark", "source_delta_pp", "movement_eligible",
    "development_borrower_excluded", "target_current_outcome_used_for_eligibility",
    "outcomes_revealed", "unit_of_analysis",
]

BOTTLENECK_FIELDS = [
    "ticker", "cik", "listed_status", "report_period_end", "report_period_label",
    "aggregated_facilities", "current_period_facilities",
    "pct_non_missing_borrower", "pct_non_missing_debt_equity",
    "pct_non_missing_facility_type", "pct_non_missing_lien", "pct_non_missing_currency",
    "pct_non_missing_reference_rate", "pct_non_missing_spread", "pct_non_missing_maturity",
    "pct_non_missing_funded_status", "pct_non_missing_principal", "pct_non_missing_fair_value",
    "facilities_entering_borrower_candidate_blocks", "facility_pairs_involving_fund",
    "pairs_passing_informative_ge3", "internal_predicted_same_facility_high",
    "source_facilities_with_prior_match", "target_prior_matches",
    "verified_reporting_order_available", "source_before_target_opportunities",
    "eligible_pre_reveal_observations", "movement_eligible_observations",
    "first_loss_stage", "dominant_exclusion_reason",
]

LOSS_LABELS = {
    "A": "A_missing_reporting_calendar",
    "B": "B_weak_XBRL_tagging",
    "C": "C_borrower_matching",
    "D": "D_facility_matching",
    "E": "E_missing_prior_quarter_position",
    "F": "F_insufficient_reporting_window",
    "G": "G_limited_19_fund_universe",
}


def seen_aliases():
    return {alias for aliases in SEEN_DEVELOPMENT_BORROWERS.values() for alias in aliases}


def mark(row):
    direct = decimal_or_none(row.get("mark_fv_to_principal"))
    if direct is not None:
        return direct
    principal = decimal_or_none(row.get("principal"))
    fair_value = decimal_or_none(row.get("fair_value"))
    return None if principal in (None, 0) or fair_value is None else fair_value / principal


def reporting_maps(rows):
    timestamps = {}
    statuses = {}
    ciks = {}
    listed = {}
    for row in rows:
        key = (row["ticker"], row["report_period_end"])
        ciks[row["ticker"]] = row["cik"]
        listed[row["ticker"]] = row["listed_status"]
        statuses[key] = row["verification_status"]
        if row["verification_status"] != "explicit_missing" and row["acceptance_timestamp_utc"]:
            timestamps[key] = row["acceptance_timestamp_utc"]
    return timestamps, statuses, ciks, listed


def utc_iso(value):
    return parse_timestamp(value).isoformat().replace("+00:00", "Z")


def index_current(rows):
    by_period_ticker_borrower = defaultdict(list)
    by_period_ticker = defaultdict(list)
    by_id = {}
    for row in rows:
        by_id[row["economic_facility_id"]] = row
        if row["is_current_period"] != "True":
            continue
        by_period_ticker_borrower[(row["period_end"], row["ticker"], row["borrower_norm"])].append(row)
        by_period_ticker[(row["period_end"], row["ticker"])].append(row)
    return by_id, by_period_ticker_borrower, by_period_ticker


def public_timestamp(facility, result_timestamps):
    results = result_timestamps.get((facility["ticker"], facility["period_end"]))
    return facility["accepted"] if not results else later_timestamp(results, facility["accepted"])


def build_eligible(facilities, reporting_rows):
    by_id, indexed, _ = index_current(facilities)
    results, _, ciks, listed_status = reporting_maps(reporting_rows)
    listed_targets = {ticker for ticker, status in listed_status.items() if status == "listed"}
    all_sources = set(listed_status)
    excluded = seen_aliases()
    observations = []
    diagnostic = Counter()
    for source in facilities:
        if source["is_current_period"] != "True" or source["ticker"] not in all_sources:
            continue
        if source["borrower_norm"] in excluded:
            diagnostic["development_borrower_excluded"] += 1
            continue
        period_end = source["period_end"]
        source_results = results.get((source["ticker"], period_end))
        if not source_results:
            diagnostic["source_reporting_missing"] += 1
            continue
        source_information = later_timestamp(source_results, source["accepted"])
        prior_period = previous_quarter_end(period_end)
        source_prior = unique_match(
            source, indexed.get((prior_period, source["ticker"], source["borrower_norm"]), [])
        )
        if not source_prior:
            diagnostic["source_prior_not_unique"] += 1
            continue
        source_prior_public = public_timestamp(source_prior, results)
        if parse_timestamp(source_prior_public) >= parse_timestamp(source_information):
            diagnostic["source_prior_not_public"] += 1
            continue
        current_mark = mark(source)
        prior_mark = mark(source_prior)
        delta = None if current_mark is None or prior_mark is None else current_mark - prior_mark
        for target_ticker in sorted(listed_targets - {source["ticker"]}):
            target_cutoff = results.get((target_ticker, period_end))
            if not target_cutoff:
                diagnostic["target_reporting_missing"] += 1
                continue
            target_prior = unique_match(
                source, indexed.get((prior_period, target_ticker, source["borrower_norm"]), [])
            )
            if not target_prior:
                diagnostic["target_prior_not_unique"] += 1
                continue
            target_prior_public = public_timestamp(target_prior, results)
            if parse_timestamp(target_prior_public) >= parse_timestamp(source_information):
                diagnostic["target_prior_not_public_before_source"] += 1
                continue
            if parse_timestamp(source_information) >= parse_timestamp(target_cutoff):
                diagnostic["source_not_before_target"] += 1
                continue
            window_days = (
                parse_timestamp(target_cutoff) - parse_timestamp(source_information)
            ).total_seconds() / 86400
            observation_id = "SN3X_" + stable_id(
                period_end, source["economic_facility_id"], source_prior["economic_facility_id"],
                target_prior["economic_facility_id"], target_ticker, length=28,
            )
            observations.append({
                "observation_id": observation_id,
                "report_period_end": period_end,
                "report_period_label": quarter_label(period_end),
                "borrower_norm": source["borrower_norm"],
                "source_ticker": source["ticker"],
                "source_cik": source["cik"],
                "source_listed_status": listed_status[source["ticker"]],
                "target_ticker": target_ticker,
                "target_cik": ciks[target_ticker],
                "source_facility_id": source["economic_facility_id"],
                "source_prior_facility_id": source_prior["economic_facility_id"],
                "target_prior_facility_id": target_prior["economic_facility_id"],
                "source_results_timestamp_utc": utc_iso(source_results),
                "source_mark_public_timestamp_utc": utc_iso(source["accepted"]),
                "source_information_timestamp_utc": utc_iso(source_information),
                "source_mark_public_evidence": "SOI acceptance; no earlier exact facility mark verified in EX-99",
                "target_prior_public_timestamp_utc": utc_iso(target_prior_public),
                "target_cutoff_timestamp_utc": utc_iso(target_cutoff),
                "reporting_window_days": f"{window_days:.6f}",
                "source_current_mark": "" if current_mark is None else f"{current_mark:.10f}",
                "source_prior_mark": "" if prior_mark is None else f"{prior_mark:.10f}",
                "source_delta_mark": "" if delta is None else f"{delta:.10f}",
                "source_delta_pp": "" if delta is None else f"{delta * 100:.6f}",
                "movement_eligible": str(delta is not None and abs(delta) >= MOVEMENT_THRESHOLD),
                "development_borrower_excluded": "False",
                "target_current_outcome_used_for_eligibility": "False",
                "outcomes_revealed": "False",
                "unit_of_analysis": "source BDC x report period x borrower x economic_facility_v2",
            })
    deduplicated = {row["observation_id"]: row for row in observations}
    return sorted(deduplicated.values(), key=lambda row: row["observation_id"]), diagnostic, by_id


def period_movement_summary(observations, reporting_rows):
    periods = {}
    period_map = {
        row["report_period_label"]: row["report_period_end"] for row in reporting_rows
    }
    for label in sorted(period_map):
        rows = [row for row in observations if row["report_period_label"] == label]
        computable = [row for row in rows if row["source_delta_mark"] != ""]
        movement_rows = [row for row in computable if row["movement_eligible"] == "True"]
        unique_movements = {
            (row["source_ticker"], row["source_facility_id"]): row for row in movement_rows
        }
        windows = [float(row["reporting_window_days"]) for row in rows]
        if len(windows) >= 2:
            p25, _, p75 = statistics.quantiles(windows, n=4, method="inclusive")
        elif windows:
            p25 = p75 = windows[0]
        else:
            p25 = p75 = None
        periods[label] = {
            "report_period_end": period_map[label],
            "classification": "development" if label == DEVELOPMENT_QUARTER else "untouched_target_outcome_period",
            "eligible_pre_reveal_observations": len(rows),
            "observations_with_computable_source_delta": len(computable),
            "movement_eligible_observations": len(movement_rows),
            "unique_movement_source_facilities": len(unique_movements),
            "unique_movement_borrowers": len({row["borrower_norm"] for row in unique_movements.values()}),
            "source_tickers": sorted({row["source_ticker"] for row in rows}),
            "target_tickers": sorted({row["target_ticker"] for row in rows}),
            "movement_source_tickers": dict(sorted(Counter(row["source_ticker"] for row in unique_movements.values()).items())),
            "reporting_window_days": {
                "p25": None if p25 is None else round(p25, 6),
                "median": None if not windows else round(statistics.median(windows), 6),
                "p75": None if p75 is None else round(p75, 6),
            },
        }
    return periods


def tagging_ready(row):
    if not row["borrower_norm"] or row["borrower_norm"] in GENERIC_BORROWERS:
        return False
    informative = sum(
        row[field] not in MISSING
        for field in ("debt_equity", "facility_type", "lien", "currency", "reference_rate", "funded_status")
    )
    informative += int(decimal_or_none(row.get("spread")) is not None)
    informative += int(bool(row.get("maturity")))
    return informative >= 3


def build_funnel(facilities, reporting_rows):
    _, indexed, by_period_ticker = index_current(facilities)
    results, _, _, listed_status = reporting_maps(reporting_rows)
    listed_targets = {ticker for ticker, status in listed_status.items() if status == "listed"}
    excluded = seen_aliases()
    losses = Counter()
    by_fund_period = defaultdict(Counter)
    eligible_count = 0
    source_prior_ids = defaultdict(set)
    target_prior_ids = defaultdict(set)
    timing_opportunities = defaultdict(int)

    for (period_end, source_ticker), source_rows in sorted(by_period_ticker.items()):
        prior_period = previous_quarter_end(period_end)
        for source in source_rows:
            if source["borrower_norm"] in excluded:
                continue
            targets = sorted(listed_targets - {source_ticker})
            any_overlap = any(
                indexed.get((prior_period, target, source["borrower_norm"]))
                for target in targets
            )
            source_prior = unique_match(
                source, indexed.get((prior_period, source_ticker, source["borrower_norm"]), [])
            )
            if source_prior:
                source_prior_ids[(source_ticker, period_end)].add(source["economic_facility_id"])
            for target in targets:
                counter = by_fund_period[(source_ticker, period_end)]
                if not results.get((source_ticker, period_end)) or not results.get((target, period_end)):
                    loss = "A"
                elif not tagging_ready(source):
                    loss = "B"
                elif not any_overlap:
                    loss = "G"
                else:
                    target_options = indexed.get((prior_period, target, source["borrower_norm"]), [])
                    if not target_options:
                        loss = "C"
                    else:
                        target_prior = unique_match(source, target_options)
                        if not target_prior:
                            loss = "D"
                        elif not source_prior:
                            loss = "E"
                        else:
                            target_prior_ids[(target, period_end)].add(target_prior["economic_facility_id"])
                            source_info = public_timestamp(source, results)
                            target_prior_public = public_timestamp(target_prior, results)
                            target_cutoff = results[(target, period_end)]
                            if (
                                parse_timestamp(target_prior_public) >= parse_timestamp(source_info)
                                or parse_timestamp(source_info) >= parse_timestamp(target_cutoff)
                            ):
                                loss = "F"
                            else:
                                eligible_count += 1
                                timing_opportunities[(source_ticker, period_end)] += 1
                                counter["eligible"] += 1
                                continue
                losses[loss] += 1
                counter[loss] += 1

    total = sum(losses.values()) + eligible_count
    dominant_code, dominant_count = losses.most_common(1)[0] if losses else ("", 0)
    return {
        "possible_directional_source_facility_target_observations": total,
        "eligible_pre_reveal_observations": eligible_count,
        "first_loss_counts": {LOSS_LABELS[key]: losses[key] for key in LOSS_LABELS},
        "first_loss_percent_of_possible": {
            LOSS_LABELS[key]: round(losses[key] / total * 100, 3) if total else 0.0
            for key in LOSS_LABELS
        },
        "primary_bottleneck_code": dominant_code,
        "primary_bottleneck": LOSS_LABELS.get(dominant_code, "none"),
        "primary_bottleneck_count": dominant_count,
        "primary_bottleneck_percent_of_otherwise_possible": round(dominant_count / total * 100, 3) if total else 0.0,
        "category_definitions": LOSS_LABELS,
        "denominator_definition": "non-seen current source economic_facility_v2 rows x other listed target funds",
        "target_current_outcome_used": False,
    }, by_fund_period, source_prior_ids, target_prior_ids, timing_opportunities


def pct_non_missing(rows, field):
    if not rows:
        return 0.0
    if field in {"spread", "principal", "fair_value"}:
        present = sum(decimal_or_none(row.get(field)) is not None for row in rows)
    elif field == "borrower_norm":
        present = sum(bool(row.get(field)) and row[field] not in GENERIC_BORROWERS for row in rows)
    else:
        present = sum(row.get(field, "") not in MISSING for row in rows)
    return round(present / len(rows) * 100, 3)


def bottleneck_rows(
    facilities, candidates, reporting_rows, eligible, movement_periods,
    by_fund_period, source_prior_ids, target_prior_ids, timing_opportunities,
):
    _, _, by_period_ticker = index_current(facilities)
    results, _, ciks, listed_status = reporting_maps(reporting_rows)
    all_by_filing_period = defaultdict(list)
    for row in facilities:
        all_by_filing_period[(row["period_end"], row["ticker"])].append(row)
    pair_rows = defaultdict(list)
    for row in candidates:
        pair_rows[(row["period_end"], row["left_ticker"])].append((row, "left"))
        pair_rows[(row["period_end"], row["right_ticker"])].append((row, "right"))
    eligible_by_key = Counter((row["source_ticker"], row["report_period_end"]) for row in eligible)
    movement_by_key = Counter(
        (row["source_ticker"], row["report_period_end"])
        for row in eligible if row["movement_eligible"] == "True"
    )
    period_ends = sorted({row["report_period_end"] for row in reporting_rows})
    listed_targets = {ticker for ticker, status in listed_status.items() if status == "listed"}
    output = []
    for period_end in period_ends:
        for ticker in sorted(ciks):
            current = by_period_ticker.get((period_end, ticker), [])
            all_rows = all_by_filing_period.get((period_end, ticker), [])
            pairs = pair_rows.get((period_end, ticker), [])
            entering = {
                row[f"{side}_row_id"] for row, side in pairs
            }
            losses = by_fund_period.get((ticker, period_end), Counter())
            if losses:
                first_code, _ = losses.most_common(1)[0]
                first_loss = LOSS_LABELS.get(first_code, "none")
            elif not current:
                first_loss = "no_current_period_facilities"
            else:
                first_loss = "none"
            if current and (ticker, period_end) in results:
                source_information = public_timestamp(current[0], results)
                calendar_opportunities = sum(
                    target != ticker
                    and (target, period_end) in results
                    and parse_timestamp(source_information) < parse_timestamp(results[(target, period_end)])
                    for target in listed_targets
                )
            else:
                calendar_opportunities = 0
            output.append({
                "ticker": ticker,
                "cik": ciks[ticker],
                "listed_status": listed_status[ticker],
                "report_period_end": period_end,
                "report_period_label": quarter_label(period_end),
                "aggregated_facilities": len(all_rows),
                "current_period_facilities": len(current),
                "pct_non_missing_borrower": pct_non_missing(current, "borrower_norm"),
                "pct_non_missing_debt_equity": pct_non_missing(current, "debt_equity"),
                "pct_non_missing_facility_type": pct_non_missing(current, "facility_type"),
                "pct_non_missing_lien": pct_non_missing(current, "lien"),
                "pct_non_missing_currency": pct_non_missing(current, "currency"),
                "pct_non_missing_reference_rate": pct_non_missing(current, "reference_rate"),
                "pct_non_missing_spread": pct_non_missing(current, "spread"),
                "pct_non_missing_maturity": pct_non_missing(current, "maturity"),
                "pct_non_missing_funded_status": pct_non_missing(current, "funded_status"),
                "pct_non_missing_principal": pct_non_missing(current, "principal"),
                "pct_non_missing_fair_value": pct_non_missing(current, "fair_value"),
                "facilities_entering_borrower_candidate_blocks": len(entering),
                "facility_pairs_involving_fund": len(pairs),
                "pairs_passing_informative_ge3": sum(int(row["informative_matches"]) >= 3 for row, _ in pairs),
                "internal_predicted_same_facility_high": sum(
                    row["predicted_label"] == "same_facility" and row["match_confidence"] == "high"
                    for row, _ in pairs
                ),
                "source_facilities_with_prior_match": len(source_prior_ids.get((ticker, period_end), set())),
                "target_prior_matches": len(target_prior_ids.get((ticker, period_end), set())),
                "verified_reporting_order_available": str((ticker, period_end) in results),
                "source_before_target_opportunities": calendar_opportunities,
                "eligible_pre_reveal_observations": eligible_by_key[(ticker, period_end)],
                "movement_eligible_observations": movement_by_key[(ticker, period_end)],
                "first_loss_stage": first_loss,
                "dominant_exclusion_reason": first_loss,
            })
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--facilities", type=Path, default=DEFAULT_FACILITIES)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--reporting", type=Path, default=DEFAULT_REPORTING)
    parser.add_argument("--eligible-output", type=Path, default=DEFAULT_ELIGIBLE)
    parser.add_argument("--movement-output", type=Path, default=DEFAULT_MOVEMENT)
    parser.add_argument("--bottleneck-output", type=Path, default=DEFAULT_BOTTLENECK)
    parser.add_argument("--funnel-output", type=Path, default=DEFAULT_FUNNEL)
    args = parser.parse_args()
    facilities = read_csv(args.facilities)
    candidates = read_csv(args.candidates)
    reporting = read_csv(args.reporting)
    eligible, diagnostics, _ = build_eligible(facilities, reporting)
    write_csv(args.eligible_output, eligible, ELIGIBLE_FIELDS)
    periods = period_movement_summary(eligible, reporting)
    untouched = [value for value in periods.values() if value["classification"].startswith("untouched")]
    movement_total = sum(value["unique_movement_source_facilities"] for value in untouched)
    movement = {
        "aggregated_input_sha256": sha256_file(args.facilities),
        "reporting_order_extended_sha256": sha256_file(args.reporting),
        "eligible_output_sha256": sha256_file(args.eligible_output),
        "movement_definition": "abs(source_current_aggregated_mark - source_prior_aggregated_mark) >= 0.005",
        "source_information_timestamp_rule": "max(verified source results timestamp, source SOI acceptance); no earlier facility mark claimed without EX-99 evidence",
        "development_borrowers_excluded_globally": sorted(SEEN_DEVELOPMENT_BORROWERS),
        "development_quarter_excluded_from_power_guard": DEVELOPMENT_QUARTER,
        "periods": periods,
        "untouched_independent_movement_facilities_total": movement_total,
        "power_guard_minimum": 20,
        "power_guard_passed_for_planning": movement_total >= 20,
        "freeze_or_reveal_authorized": False,
        "target_current_outcome_used": False,
        "eligibility_diagnostics": dict(sorted(diagnostics.items())),
    }
    write_json(args.movement_output, movement)
    funnel, by_fund_period, source_prior_ids, target_prior_ids, timing = build_funnel(facilities, reporting)
    funnel.update({
        "aggregated_input_sha256": sha256_file(args.facilities),
        "reporting_order_extended_sha256": sha256_file(args.reporting),
        "eligible_output_sha256": sha256_file(args.eligible_output),
    })
    write_json(args.funnel_output, funnel)
    bottleneck = bottleneck_rows(
        facilities, candidates, reporting, eligible, periods,
        by_fund_period, source_prior_ids, target_prior_ids, timing,
    )
    write_csv(args.bottleneck_output, bottleneck, BOTTLENECK_FIELDS)
    print(json.dumps({
        "eligible_count": len(eligible),
        "periods": periods,
        "movement_total_untouched": movement_total,
        "power_guard_passed": movement_total >= 20,
        "primary_bottleneck": funnel["primary_bottleneck"],
        "primary_bottleneck_percent": funnel["primary_bottleneck_percent_of_otherwise_possible"],
        "bottleneck_rows": len(bottleneck),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

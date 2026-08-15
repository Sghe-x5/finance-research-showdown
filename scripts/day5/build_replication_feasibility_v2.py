#!/usr/bin/env python3
"""Recompute Day 5 feasibility with new periods and verified fund metadata."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import statistics
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE_PATH = ROOT / "scripts/day5/build_replication_feasibility.py"
SPEC = importlib.util.spec_from_file_location("day5_feasibility_v1", BASE_PATH)
base = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(base)


HISTORICAL_PERIODS = {
    "2024-03-31", "2024-06-30", "2024-09-30", "2024-12-31",
    "2025-03-31", "2025-06-30",
}
NEW_INCLUDED_PERIODS = {"2026-03-31"}
INCLUDED_PERIODS = HISTORICAL_PERIODS | NEW_INCLUDED_PERIODS
CONTEXT_PERIODS = INCLUDED_PERIODS | {"2023-12-31", "2025-09-30", "2025-12-31"}
CONTAMINATED_PERIODS = {"2025-09-30", "2025-12-31"}

DEFAULT_HISTORICAL = Path("/private/tmp/finance-day3-sec-cache/bdc_facilities_all_agg.csv")
DEFAULT_NEW = Path("/private/tmp/finance-day5-sec-cache/bdc_facilities_2026_new_agg.csv")
DEFAULT_UNIVERSE = Path("data/day3/universe_expansion_estimate.csv")
DEFAULT_MANAGER_OLD = Path("data/day3/bdc_manager_map.csv")
DEFAULT_REPORTING_OLD = Path("data/day3/reporting_order_extended.csv")
DEFAULT_DAY4_SAMPLE = Path("data/day4/confirmatory_included_sample.csv")
DEFAULT_MANAGER_VERIFIED = Path("data/day5/new_fund_manager_map_verified.csv")
DEFAULT_LISTING_VERIFIED = Path("data/day5/new_fund_listing_status_verified.csv")
DEFAULT_REPORTING_VERIFIED = Path("data/day5/new_fund_reporting_order_verified.csv")
DEFAULT_INDEPENDENCE = Path("data/day5/new_period_independence_audit.json")
DEFAULT_OUTPUT = Path("data/day5/replication_universe_candidates_v2.csv")
DEFAULT_SUMMARY = Path("data/day5/replication_feasibility_summary_v2.json")
DEFAULT_REPORT = Path("docs/research/DAY5_REPLICATION_FEASIBILITY_V2.md")


def configure_base() -> None:
    base.PRIMARY_PERIODS = set(INCLUDED_PERIODS)
    base.STANDARD_PERIODS = set(CONTEXT_PERIODS)
    base.DEVELOPMENT_PERIOD = "2025-09-30"


def merge_periods(left, right):
    output = {key: set(values) for key, values in left.items()}
    for key, values in right.items():
        output.setdefault(key, set()).update(values)
    return output


def augment_metadata_from_new_cache(metadata: dict, path: Path) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            cik = str(int(row["cik"]))
            metadata.setdefault(cik, {
                "cik": cik,
                "fund_id": row["ticker"] or f"CIK{cik}",
                "filer_name": row["filer_name"],
                "listed_status": "unknown",
                "recommended_include_later": "False",
                "canonical_manager": "",
            })


def provisional_context(
    historical_path: Path = DEFAULT_HISTORICAL,
    new_path: Path = DEFAULT_NEW,
    universe_path: Path = DEFAULT_UNIVERSE,
    manager_old_path: Path = DEFAULT_MANAGER_OLD,
    reporting_old_path: Path = DEFAULT_REPORTING_OLD,
    day4_sample_path: Path = DEFAULT_DAY4_SAMPLE,
):
    configure_base()
    metadata, existing_ciks = base.load_fund_metadata(universe_path, manager_old_path)
    augment_metadata_from_new_cache(metadata, new_path)
    historical, historical_acceptance, historical_periods = base.load_facilities(
        historical_path, metadata
    )
    new, new_acceptance, new_periods = base.load_facilities(new_path, metadata)
    facilities = historical + new
    acceptances = {**historical_acceptance, **new_acceptance}
    periods_by_cik = merge_periods(historical_periods, new_periods)
    day4_borrowers, day4_clusters, development = base.load_exclusions(day4_sample_path)
    old_cutoffs = base.load_verified_cutoffs(reporting_old_path)
    candidates, diagnostics = base.build_candidates(
        facilities, metadata, existing_ciks, acceptances, old_cutoffs,
        day4_borrowers, day4_clusters, development,
    )
    return {
        "metadata": metadata,
        "existing_ciks": existing_ciks,
        "facilities": facilities,
        "acceptances": acceptances,
        "periods_by_cik": periods_by_cik,
        "day4_borrowers": day4_borrowers,
        "day4_clusters": day4_clusters,
        "development": development,
        "old_cutoffs": old_cutoffs,
        "candidates": candidates,
        "diagnostics": diagnostics,
    }


def new_fund_scope(context: dict) -> set[str]:
    existing = context["existing_ciks"]
    return {
        str(cik)
        for row in context["candidates"]
        for cik in (row["source_cik"], row["target_cik"])
        if str(cik) not in existing
    }


def target_scope(context: dict) -> set[tuple[str, str]]:
    return {
        (str(row["target_cik"]), str(row["period_end"]))
        for row in context["candidates"]
    }


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def verified_inputs(
    context: dict,
    manager_path: Path,
    listing_path: Path,
    reporting_path: Path,
):
    manager_rows = read_rows(manager_path)
    listing_rows = read_rows(listing_path)
    reporting_rows = read_rows(reporting_path)
    manager_map = {
        str(int(row["cik"])): row
        for row in manager_rows if row["verification_status"] == "verified"
    }
    listing_map = {
        str(int(row["cik"])): row for row in listing_rows
    }
    cutoffs = dict(context["old_cutoffs"])
    for row in reporting_rows:
        if row["verification_status"] != "verified" or not row["acceptance_timestamp_utc"]:
            continue
        cutoffs[(str(int(row["cik"])), row["report_period_end"])] = row[
            "acceptance_timestamp_utc"
        ]
    return manager_map, listing_map, cutoffs, reporting_rows


def verified_candidates(context: dict, manager_map: dict, listing_map: dict, cutoffs: dict):
    metadata = {cik: dict(values) for cik, values in context["metadata"].items()}
    existing = context["existing_ciks"]
    for cik, values in metadata.items():
        if cik in existing:
            continue
        manager = manager_map.get(cik)
        values["canonical_manager"] = manager["canonical_manager"] if manager else ""
        listing = listing_map.get(cik, {})
        if listing.get("listing_status") == "verified_listed_equity":
            values["listed_status"] = "listed"
            values["fund_id"] = listing["verified_equity_ticker"]
        else:
            values["listed_status"] = "non-listed"
            values["fund_id"] = f"CIK{cik}"
    facilities = []
    for source in context["facilities"]:
        row = dict(source)
        row["fund_id"] = metadata[row["cik"]]["fund_id"]
        facilities.append(row)
    candidates, diagnostics = base.build_candidates(
        facilities, metadata, existing, context["acceptances"], cutoffs,
        context["day4_borrowers"], context["day4_clusters"], context["development"],
    )
    verified = []
    exclusions = Counter()
    for row in candidates:
        if row["period_end"] not in INCLUDED_PERIODS:
            exclusions["period_not_included"] += 1
            continue
        source_cik = str(row["source_cik"])
        target_cik = str(row["target_cik"])
        if source_cik not in existing and source_cik not in manager_map:
            exclusions["source_manager_unverified"] += 1
            continue
        if target_cik not in existing and target_cik not in manager_map:
            exclusions["target_manager_unverified"] += 1
            continue
        if target_cik not in existing and listing_map.get(target_cik, {}).get(
            "listing_status"
        ) != "verified_listed_equity":
            exclusions["target_not_verified_listed_equity"] += 1
            continue
        if row["target_cutoff_basis"] != "verified_earliest_results_day3":
            exclusions["target_timing_proxy_not_verified"] += 1
            continue
        verified.append(row)
    base.validate_output(verified)
    return verified, diagnostics, dict(sorted(exclusions.items())), metadata


def relationship_counts(rows: list[dict[str, object]], flag: str) -> dict:
    selected = [row for row in rows if row[flag] == "True"]
    windows = [float(row["reporting_window_days"]) for row in selected]
    return {
        "observations": len(selected),
        "source_event_clusters": len({row["source_event_cluster_id"] for row in selected}),
        "unique_borrowers": len({row["normalized_borrower"] for row in selected}),
        "additional_funds": len({
            str(cik)
            for row in selected
            for cik, is_new in (
                (row["source_cik"], row["source_is_new_fund"]),
                (row["target_cik"], row["target_is_new_fund"]),
            )
            if is_new == "True"
        }),
        "source_target_pairs": len({
            (row["source_fund_id"], row["target_fund_id"]) for row in selected
        }),
        "counts_by_quarter": dict(sorted(Counter(row["report_period_label"] for row in selected).items())),
        "counts_by_source": dict(sorted(Counter(row["source_fund_id"] for row in selected).items())),
        "counts_by_target": dict(sorted(Counter(row["target_fund_id"] for row in selected).items())),
        "reporting_window_days": {
            "p25": base.percentile(windows, 0.25),
            "median": statistics.median(windows) if windows else None,
            "p75": base.percentile(windows, 0.75),
            "min": min(windows) if windows else None,
            "max": max(windows) if windows else None,
        },
        "requires_human_facility_review": len(selected),
    }


def write_report(path: Path, summary: dict) -> None:
    strict = summary["strict_new_borrower"]
    supporting = summary["supporting_new_fund"]
    lines = [
        "# Day 5 ShadowNAV replication feasibility V2",
        "",
        "## Boundary",
        "",
        "This is an outcome-blind feasibility expansion. No Day 5 sample is frozen and no",
        "target same-period numeric value, prediction, error, or inferential result is materialized.",
        "The Day 4 hypothesis, economic_facility_v2 aggregation, matcher, and six decision",
        "criteria remain unchanged.",
        "",
        "## Official archive expansion",
        "",
        "The official SEC monthly BDC archives 2026_01 through 2026_06 were inventoried",
        "and cached outside Git. June has no financial SOI table, consistent with the SEC note.",
        "The locked pipeline recovered 2025-12-31 and 2026-03-31 facility contexts.",
        "",
        "## Period independence",
        "",
        "2025Q4 is excluded as a replication outcome period because Auctane and Medallia",
        "target outcomes from that period were inspected as quarantined Day 2 calculation",
        "fixtures. It is used only as prior-quarter context for 2026Q1. The 2026Q1 period",
        "passes the pre-outcome independence checks and is included.",
        "",
        "## Verified clean maxima",
        "",
        "| Universe | Observations | Source-event clusters | Borrowers | Additional funds | Fund pairs |",
        "|---|---:|---:|---:|---:|---:|",
        f"| Strict new-borrower | {strict['observations']} | {strict['source_event_clusters']} | {strict['unique_borrowers']} | {strict['additional_funds']} | {strict['source_target_pairs']} |",
        f"| Supporting new-fund | {supporting['observations']} | {supporting['source_event_clusters']} | {supporting['unique_borrowers']} | {supporting['additional_funds']} | {supporting['source_target_pairs']} |",
        "",
        "### Quarter contributions",
        "",
        f"Strict: `{json.dumps(strict['counts_by_quarter'], sort_keys=True)}`.",
        "",
        f"Supporting: `{json.dumps(supporting['counts_by_quarter'], sort_keys=True)}`.",
        "",
        "## Verification and attrition",
        "",
        f"- Same-manager rows excluded from the primary layer: {summary['verification_attrition']['same_manager_candidates']}.",
        f"- Target rows excluded for unverified listed-equity status: {summary['verification_attrition']['target_not_verified_listed_equity']}.",
        f"- Timing-proxy rows excluded after verification: {summary['verification_attrition']['timing_proxy_rows_excluded_after_verification']}.",
        f"- Rows newly enabled by a verified cutoff: {summary['verification_attrition']['rows_newly_enabled_by_verified_cutoff']}.",
        f"- Common candidate cutoff timestamps changed: {summary['verification_attrition']['cutoff_timestamp_changes_on_common_candidates']}.",
        f"- Duplicate vote identities: {summary['duplicate_vote_audit']['duplicate_identities']}.",
        "",
        "## Planning decision",
        "",
        (
            "The planning target of at least 50 borrowers and 80 independent source-event clusters "
            + ("appears achievable before human review." if summary["planning_target"]["appears_feasible"] else "does not appear achievable in the verified clean maximum.")
        ),
        "",
        "No sample freeze, outcome reveal, replication decision, or results tag is authorized by this report.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical-facilities", type=Path, default=DEFAULT_HISTORICAL)
    parser.add_argument("--new-facilities", type=Path, default=DEFAULT_NEW)
    parser.add_argument("--manager-verified", type=Path, default=DEFAULT_MANAGER_VERIFIED)
    parser.add_argument("--listing-verified", type=Path, default=DEFAULT_LISTING_VERIFIED)
    parser.add_argument("--reporting-verified", type=Path, default=DEFAULT_REPORTING_VERIFIED)
    parser.add_argument("--independence-audit", type=Path, default=DEFAULT_INDEPENDENCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    independence = json.loads(args.independence_audit.read_text(encoding="utf-8"))
    if independence["periods"]["2026Q1"]["overall_status"] != "PASS_UNTOUCHED":
        raise RuntimeError("2026Q1 independence audit did not pass")
    if independence["periods"]["2025Q4"]["included_as_replication_outcome_period"]:
        raise RuntimeError("Contaminated 2025Q4 cannot enter the replication outcome period set")
    context = provisional_context(args.historical_facilities, args.new_facilities)
    manager_map, listing_map, cutoffs, reporting_rows = verified_inputs(
        context, args.manager_verified, args.listing_verified, args.reporting_verified
    )
    rows, diagnostics, exclusions, metadata = verified_candidates(
        context, manager_map, listing_map, cutoffs
    )
    base.write_csv(args.output, rows)
    strict = relationship_counts(rows, "strict_new_borrower_universe")
    supporting = relationship_counts(rows, "new_fund_universe")
    duplicate_counts = Counter(row["duplicate_vote_identity"] for row in rows)
    provisional = context["candidates"]
    provisional_by_identity = {
        row["duplicate_vote_identity"]: row for row in provisional
    }
    verified_by_identity = {
        row["duplicate_vote_identity"]: row for row in rows
    }
    common_identities = set(provisional_by_identity) & set(verified_by_identity)
    new_fund_ciks = new_fund_scope(context)
    listing_excluded_rows = sum(
        str(row["target_cik"]) in new_fund_ciks
        and listing_map.get(str(row["target_cik"]), {}).get("listing_status")
        != "verified_listed_equity"
        for row in provisional
    )
    proxy_identities = {
        row["duplicate_vote_identity"] for row in provisional
        if row["target_cutoff_basis"].startswith("periodic_filing_acceptance_proxy")
    }
    summary = {
        "status": "outcome_blind_replication_feasibility_v2_only",
        "included_periods": [base.quarter_label(value) for value in sorted(INCLUDED_PERIODS)],
        "contaminated_periods_excluded": ["2025Q3", "2025Q4"],
        "strict_new_borrower": strict,
        "supporting_new_fund": supporting,
        "incremental_2025Q4": {"observations": 0, "clusters": 0, "borrowers": 0, "reason": "excluded_contaminated_period"},
        "incremental_2026Q1": {
            "strict_observations": strict["counts_by_quarter"].get("2026Q1", 0),
            "supporting_observations": supporting["counts_by_quarter"].get("2026Q1", 0),
            "strict_clusters": len({row["source_event_cluster_id"] for row in rows if row["strict_new_borrower_universe"] == "True" and row["report_period_label"] == "2026Q1"}),
            "supporting_clusters": len({row["source_event_cluster_id"] for row in rows if row["new_fund_universe"] == "True" and row["report_period_label"] == "2026Q1"}),
            "strict_borrowers": len({row["normalized_borrower"] for row in rows if row["strict_new_borrower_universe"] == "True" and row["report_period_label"] == "2026Q1"}),
            "supporting_borrowers": len({row["normalized_borrower"] for row in rows if row["new_fund_universe"] == "True" and row["report_period_label"] == "2026Q1"}),
        },
        "verification_attrition": {
            "same_manager_candidates": sum(row["manager_relationship"] == "same_manager" for row in rows),
            "target_not_verified_listed_equity": listing_excluded_rows,
            "target_timing_proxy_rows_before_verification": len(proxy_identities),
            "timing_proxy_rows_excluded_after_verification": len(proxy_identities - set(verified_by_identity)),
            "rows_newly_enabled_by_verified_cutoff": len(set(verified_by_identity) - set(provisional_by_identity)),
            "cutoff_timestamp_changes_on_common_candidates": sum(
                provisional_by_identity[key]["target_cutoff_timestamp_utc"]
                != verified_by_identity[key]["target_cutoff_timestamp_utc"]
                for key in common_identities
            ),
            "source_manager_unverified": exclusions.get("source_manager_unverified", 0),
            "target_manager_unverified": exclusions.get("target_manager_unverified", 0),
            "provisional_candidate_rows": len(provisional),
            "verified_candidate_rows": len(rows),
        },
        "duplicate_vote_audit": {
            "duplicate_identities": sum(value > 1 for value in duplicate_counts.values()),
            "duplicate_rows": sum(value - 1 for value in duplicate_counts.values() if value > 1),
        },
        "planning_target": {
            "borrowers": 50,
            "clusters": 80,
            "appears_feasible": strict["unique_borrowers"] >= 50 and strict["source_event_clusters"] >= 80,
            "planning_only_not_decision_criterion": True,
        },
        "locked_rules": {
            "economic_facility": "economic_facility_v2",
            "movement_threshold": 0.005,
            "matcher_changed": False,
            "hypothesis_changed": False,
            "decision_criteria_changed": False,
        },
        "prohibitions": {
            "target_same_period_numeric_values_materialized": False,
            "predictions_or_errors_calculated": False,
            "inferential_statistics_calculated": False,
            "sample_frozen": False,
            "result_tag_created": False,
        },
        "input_sha256": {
            "historical_facilities": base.sha256_file(args.historical_facilities),
            "new_facilities": base.sha256_file(args.new_facilities),
            "manager_verified": base.sha256_file(args.manager_verified),
            "listing_verified": base.sha256_file(args.listing_verified),
            "reporting_verified": base.sha256_file(args.reporting_verified),
            "independence_audit": base.sha256_file(args.independence_audit),
        },
    }
    summary["candidate_file_sha256"] = base.sha256_file(args.output)
    base.write_json(args.summary, summary)
    write_report(args.report, summary)
    print(json.dumps({
        "strict": strict,
        "supporting": supporting,
        "incremental_2026Q1": summary["incremental_2026Q1"],
        "planning_target_appears_feasible": summary["planning_target"]["appears_feasible"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

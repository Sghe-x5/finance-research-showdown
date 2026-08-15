#!/usr/bin/env python3
"""Build the outcome-blind Day 5 ShadowNAV replication feasibility universe.

The builder may use a source fund's current/prior marks solely to identify the
locked >=0.5 percentage-point movement event.  It never looks up a target's
same-period numeric fields: targets enter only through a previously public
facility and a public reporting/filing timestamp.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


DAY2 = Path(__file__).resolve().parents[1] / "day2"
DAY3 = Path(__file__).resolve().parents[1] / "day3"
sys.path.insert(0, str(DAY2))
sys.path.insert(0, str(DAY3))

from build_eligible_nowcasts import strict_same_facility  # noqa: E402
from common import decimal_or_none, previous_quarter_end, quarter_label  # noqa: E402
from export_blind_match_benchmark import SEEN_DEVELOPMENT_BORROWERS  # noqa: E402


MOVEMENT_THRESHOLD = 0.005
PRIMARY_PERIODS = {
    "2024-03-31", "2024-06-30", "2024-09-30", "2024-12-31",
    "2025-03-31", "2025-06-30",
}
DEVELOPMENT_PERIOD = "2025-09-30"
STANDARD_PERIODS = PRIMARY_PERIODS | {"2023-12-31", DEVELOPMENT_PERIOD}

OUTPUT_FIELDS = (
    "candidate_observation_id",
    "source_event_cluster_id",
    "source_event_key_sha256",
    "period_end",
    "report_period_label",
    "period_classification",
    "normalized_borrower",
    "source_fund_id",
    "source_cik",
    "source_is_new_fund",
    "target_fund_id",
    "target_cik",
    "target_is_new_fund",
    "relationship_scope",
    "source_manager_family",
    "target_manager_family",
    "manager_relationship",
    "manager_mapping_basis",
    "source_facility_id",
    "source_prior_facility_id",
    "target_prior_facility_id",
    "source_mark_public_timestamp_utc",
    "target_cutoff_timestamp_utc",
    "target_cutoff_basis",
    "reporting_window_days",
    "exact_borrower_block_size",
    "strict_unique_facility_match",
    "requires_human_facility_review",
    "strict_new_borrower_universe",
    "new_fund_universe",
    "overlap_day4_borrower",
    "overlap_day4_source_event_id",
    "overlap_development_borrower",
    "duplicate_vote_identity",
)

FORBIDDEN_OUTPUT_COLUMNS = {
    "target_current_mark", "target_fair_value", "target_current_fair_value",
    "prediction_B0", "prediction_SN", "error", "absolute_error",
    "source_current_mark", "source_prior_mark", "source_delta_mark",
}


def stable_hash(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def stable_id(prefix: str, *parts: str, length: int = 24) -> str:
    return prefix + stable_hash(*parts)[:length]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00").replace(" ", "T", 1))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def utc_iso(value: str) -> str:
    return parse_timestamp(value).isoformat().replace("+00:00", "Z")


def mark(row: dict[str, str]) -> float | None:
    direct = decimal_or_none(row.get("mark_fv_to_principal"))
    if direct is not None:
        return direct
    principal = decimal_or_none(row.get("principal"))
    fair_value = decimal_or_none(row.get("fair_value"))
    if principal in (None, 0) or fair_value is None:
        return None
    return fair_value / principal


def canonical_cik(value: str) -> str:
    return str(int(value))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_fund_metadata(
    universe_path: Path,
    manager_path: Path,
) -> tuple[dict[str, dict[str, str]], set[str]]:
    metadata: dict[str, dict[str, str]] = {}
    existing_ciks = set()
    managers_by_cik = {}
    for row in read_csv(manager_path):
        cik = canonical_cik(row["cik"])
        existing_ciks.add(cik)
        managers_by_cik[cik] = row["canonical_manager"]
    for row in read_csv(universe_path):
        cik = canonical_cik(row["cik"])
        ticker = row["known_ticker"].strip() or f"CIK{cik}"
        metadata[cik] = {
            "cik": cik,
            "fund_id": ticker,
            "filer_name": row["filer_name"].strip(),
            "listed_status": row["listed_status"].strip(),
            "recommended_include_later": row["recommended_include_later"].strip(),
            "canonical_manager": managers_by_cik.get(cik, ""),
        }
    return metadata, existing_ciks


MANAGER_FAMILY_PATTERNS = (
    (("ARES ",), "Ares Management"),
    (("BARINGS",), "Barings"),
    (("BLACKSTONE",), "Blackstone Credit & Insurance"),
    (("BLACKROCK",), "BlackRock"),
    (("BLUE OWL", "OWL ROCK"), "Blue Owl Credit"),
    (("APOLLO", "MIDCAP"), "Apollo Global Management"),
    (("CARLYLE",), "Carlyle"),
    (("GOLUB",), "Golub Capital"),
    (("GOLDMAN SACHS",), "Goldman Sachs Asset Management"),
    (("HPS ",), "HPS Investment Partners"),
    (("NEW MOUNTAIN", "NMF "), "New Mountain Capital"),
    (("OAKTREE",), "Oaktree Capital Management"),
    (("SIXTH STREET",), "Sixth Street"),
    (("FS KKR", "FS/KKR"), "FS/KKR"),
    (("MAIN STREET", "MSC INCOME"), "Main Street Capital"),
    (("CAPITAL SOUTHWEST",), "Capital Southwest"),
    (("GLADSTONE",), "Gladstone"),
    (("PENNANTPARK",), "PennantPark"),
    (("OFS CAPITAL",), "OFS Capital Management"),
    (("FIDUS",), "Fidus Investment"),
    (("CION",), "CION Investments"),
    (("STELLUS",), "Stellus Capital Management"),
    (("WHITEHORSE",), "WhiteHorse Finance"),
    (("INVESTCORP",), "Investcorp"),
    (("TRIPLEPOINT",), "TriplePoint Capital"),
    (("CRESCENT",), "Crescent Capital"),
    (("GREAT ELM",), "Great Elm"),
    (("MORGAN STANLEY",), "Morgan Stanley Investment Management"),
    (("PALMER SQUARE",), "Palmer Square Capital Management"),
    (("PGIM",), "PGIM"),
    (("MONROE",), "Monroe Capital"),
    (("BC PARTNERS", "BCP INVESTMENT"), "BC Partners"),
    (("ANTARES",), "Antares Capital"),
    (("SLR ",), "SLR Capital Partners"),
    (("TCW ",), "TCW"),
    (("AB PRIVATE",), "AllianceBernstein"),
)


def manager_family(meta: dict[str, str]) -> tuple[str, str]:
    if meta["canonical_manager"]:
        return meta["canonical_manager"], "official_day3_manager_map"
    name = meta["filer_name"].upper()
    for needles, family in MANAGER_FAMILY_PATTERNS:
        if any(needle in name for needle in needles):
            return family, "deterministic_filer_name_family_proxy"
    return f"UNVERIFIED::{name}", "fund_specific_name_proxy"


def load_exclusions(day4_sample: Path) -> tuple[set[str], set[str], set[str]]:
    day4_rows = read_csv(day4_sample)
    day4_borrowers = {row["normalized_borrower"] for row in day4_rows}
    day4_clusters = {row["source_event_cluster_id"] for row in day4_rows}
    development = {
        alias
        for aliases in SEEN_DEVELOPMENT_BORROWERS.values()
        for alias in aliases
    }
    return day4_borrowers, day4_clusters, development


def load_facilities(path: Path, metadata: dict[str, dict[str, str]]):
    """Load only standard-quarter current facilities and required fields.

    Numeric columns remain needed only for a row acting as the source of a
    movement event.  No target same-period row is joined to an observation.
    """
    fields = {
        "economic_facility_id", "accepted", "cik", "ticker", "filer_name",
        "period_end", "is_current_period", "borrower_norm", "debt_equity",
        "facility_type", "lien", "currency", "reference_rate", "spread",
        "maturity", "funded_status", "acquisition_date", "principal",
        "fair_value", "mark_fv_to_principal", "aggregation_rule_version",
    }
    rows = []
    period_acceptances: dict[tuple[str, str], str] = {}
    periods_by_cik: dict[str, set[str]] = defaultdict(set)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = fields - set(reader.fieldnames or [])
        if missing:
            raise RuntimeError(f"Aggregate is missing fields: {sorted(missing)}")
        for raw in reader:
            if raw["is_current_period"] != "True" or raw["period_end"] not in STANDARD_PERIODS:
                continue
            cik = canonical_cik(raw["cik"])
            if cik not in metadata or not raw["borrower_norm"]:
                continue
            row = {field: raw[field] for field in fields}
            row["cik"] = cik
            row["fund_id"] = metadata[cik]["fund_id"]
            rows.append(row)
            periods_by_cik[cik].add(row["period_end"])
            key = (cik, row["period_end"])
            accepted = utc_iso(row["accepted"])
            if key not in period_acceptances or parse_timestamp(accepted) < parse_timestamp(period_acceptances[key]):
                period_acceptances[key] = accepted
    return rows, period_acceptances, periods_by_cik


def facility_index(rows: list[dict[str, str]]):
    output: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        output[(row["period_end"], row["cik"], row["borrower_norm"])].append(row)
    return output


def unique_strict_match(
    facility: dict[str, str], options: list[dict[str, str]],
) -> dict[str, str] | None:
    matches = [row for row in options if strict_same_facility(facility, row)]
    return matches[0] if len(matches) == 1 else None


def load_verified_cutoffs(path: Path) -> dict[tuple[str, str], str]:
    output = {}
    for row in read_csv(path):
        if row["verification_status"] == "explicit_missing" or not row["acceptance_timestamp_utc"]:
            continue
        output[(canonical_cik(row["cik"]), row["report_period_end"])] = utc_iso(
            row["acceptance_timestamp_utc"]
        )
    return output


def period_classification(period_end: str) -> str:
    if period_end in PRIMARY_PERIODS:
        return "primary_untouched_historical_window"
    if period_end == DEVELOPMENT_PERIOD:
        return "excluded_development_2025Q3"
    return "not_in_replication_window"


def build_candidates(
    facilities: list[dict[str, str]],
    metadata: dict[str, dict[str, str]],
    existing_ciks: set[str],
    period_acceptances: dict[tuple[str, str], str],
    verified_cutoffs: dict[tuple[str, str], str],
    day4_borrowers: set[str],
    day4_clusters: set[str],
    development_borrowers: set[str],
) -> tuple[list[dict[str, object]], dict]:
    index = facility_index(facilities)
    listed_targets = {
        cik for cik, meta in metadata.items() if meta["listed_status"] == "listed"
    }
    output: list[dict[str, object]] = []
    diagnostics = Counter()

    for source in facilities:
        period_end = source["period_end"]
        if period_end not in PRIMARY_PERIODS:
            continue
        prior_period = previous_quarter_end(period_end)
        source_prior_options = index.get((prior_period, source["cik"], source["borrower_norm"]), [])
        source_prior = unique_strict_match(source, source_prior_options)
        if not source_prior:
            diagnostics["source_prior_not_unique"] += 1
            continue
        source_mark = mark(source)
        prior_mark = mark(source_prior)
        if source_mark is None or prior_mark is None:
            diagnostics["source_delta_not_computable"] += 1
            continue
        if not math.isfinite(source_mark) or not math.isfinite(prior_mark):
            diagnostics["source_delta_non_finite"] += 1
            continue
        if abs(source_mark - prior_mark) < MOVEMENT_THRESHOLD:
            diagnostics["source_not_movement"] += 1
            continue

        source_is_new = source["cik"] not in existing_ciks
        source_day4_cluster = stable_id(
            "D4C_", period_end, source["fund_id"], source["economic_facility_id"]
        )
        overlaps_day4_event = source_day4_cluster in day4_clusters
        source_event_key = stable_hash(
            period_end, source["cik"], source["economic_facility_id"]
        )
        source_event_cluster = "D5C_" + source_event_key[:24]
        source_time = utc_iso(source["accepted"])

        for target_cik in sorted(listed_targets, key=int):
            if target_cik == source["cik"]:
                continue
            target_is_new = target_cik not in existing_ciks
            if not source_is_new and not target_is_new:
                continue
            target_prior_options = index.get((prior_period, target_cik, source["borrower_norm"]), [])
            if not target_prior_options:
                continue
            diagnostics["exact_borrower_blocks"] += 1
            target_manager, target_manager_basis = manager_family(metadata[target_cik])
            source_manager, source_manager_basis = manager_family(metadata[source["cik"]])
            manager_relationship = (
                "same_manager" if source_manager == target_manager else "cross_manager"
            )
            overlap_development = source["borrower_norm"] in development_borrowers
            overlap_day4_borrower = source["borrower_norm"] in day4_borrowers
            if (
                source_is_new
                and not overlap_development
                and not overlap_day4_borrower
                and not overlaps_day4_event
                and manager_relationship == "cross_manager"
            ):
                diagnostics["strict_new_borrower_exact_borrower_blocks"] += 1
            if (
                (source_is_new or target_is_new)
                and not overlaps_day4_event
                and manager_relationship == "cross_manager"
            ):
                diagnostics["new_fund_exact_borrower_blocks"] += 1
            target_prior = unique_strict_match(source, target_prior_options)
            if not target_prior:
                diagnostics["target_prior_not_unique_strict"] += 1
                continue
            if parse_timestamp(target_prior["accepted"]) >= parse_timestamp(source_time):
                diagnostics["target_prior_not_public_before_source"] += 1
                continue

            cutoff_key = (target_cik, period_end)
            if cutoff_key in verified_cutoffs:
                target_cutoff = verified_cutoffs[cutoff_key]
                cutoff_basis = "verified_earliest_results_day3"
            elif cutoff_key in period_acceptances:
                target_cutoff = period_acceptances[cutoff_key]
                cutoff_basis = "periodic_filing_acceptance_proxy_needs_results_calendar_review"
            else:
                diagnostics["target_cutoff_missing"] += 1
                continue
            if parse_timestamp(source_time) >= parse_timestamp(target_cutoff):
                diagnostics["source_not_before_target_cutoff"] += 1
                continue

            relationship_scope = (
                "new_source_new_target" if source_is_new and target_is_new
                else "new_source_existing_target" if source_is_new
                else "existing_source_new_target"
            )
            strict_new = (
                source_is_new
                and not overlap_development
                and not overlap_day4_borrower
                and not overlaps_day4_event
                and manager_relationship == "cross_manager"
            )
            new_fund = (
                not overlaps_day4_event and manager_relationship == "cross_manager"
            )
            identity = "|".join((
                period_end, source["borrower_norm"], source["cik"], target_cik,
                source["economic_facility_id"], source_prior["economic_facility_id"],
                target_prior["economic_facility_id"],
            ))
            observation_id = stable_id("D5R_", identity)
            output.append({
                "candidate_observation_id": observation_id,
                "source_event_cluster_id": source_event_cluster,
                "source_event_key_sha256": source_event_key,
                "period_end": period_end,
                "report_period_label": quarter_label(period_end),
                "period_classification": period_classification(period_end),
                "normalized_borrower": source["borrower_norm"],
                "source_fund_id": source["fund_id"],
                "source_cik": source["cik"],
                "source_is_new_fund": str(source_is_new),
                "target_fund_id": metadata[target_cik]["fund_id"],
                "target_cik": target_cik,
                "target_is_new_fund": str(target_is_new),
                "relationship_scope": relationship_scope,
                "source_manager_family": source_manager,
                "target_manager_family": target_manager,
                "manager_relationship": manager_relationship,
                "manager_mapping_basis": f"{source_manager_basis}|{target_manager_basis}",
                "source_facility_id": source["economic_facility_id"],
                "source_prior_facility_id": source_prior["economic_facility_id"],
                "target_prior_facility_id": target_prior["economic_facility_id"],
                "source_mark_public_timestamp_utc": source_time,
                "target_cutoff_timestamp_utc": target_cutoff,
                "target_cutoff_basis": cutoff_basis,
                "reporting_window_days": round(
                    (parse_timestamp(target_cutoff) - parse_timestamp(source_time)).total_seconds() / 86400,
                    6,
                ),
                "exact_borrower_block_size": len(target_prior_options),
                "strict_unique_facility_match": "True",
                "requires_human_facility_review": "True",
                "strict_new_borrower_universe": str(strict_new),
                "new_fund_universe": str(new_fund),
                "overlap_day4_borrower": str(overlap_day4_borrower),
                "overlap_day4_source_event_id": str(overlaps_day4_event),
                "overlap_development_borrower": str(overlap_development),
                "duplicate_vote_identity": identity,
            })

    output.sort(key=lambda row: str(row["candidate_observation_id"]))
    duplicate_counts = Counter(str(row["duplicate_vote_identity"]) for row in output)
    diagnostics["duplicate_vote_identities"] = sum(value > 1 for value in duplicate_counts.values())
    diagnostics["duplicate_vote_rows"] = sum(value - 1 for value in duplicate_counts.values() if value > 1)
    return output, dict(sorted(diagnostics.items()))


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def summarize_rows(rows: list[dict[str, object]], flag: str, diagnostics: dict) -> dict:
    selected = [row for row in rows if row[flag] == "True"]
    windows = [float(row["reporting_window_days"]) for row in selected]
    source_funds = Counter(str(row["source_fund_id"]) for row in selected)
    target_funds = Counter(str(row["target_fund_id"]) for row in selected)
    periods = Counter(str(row["report_period_label"]) for row in selected)
    pairs = Counter(f"{row['source_fund_id']}->{row['target_fund_id']}" for row in selected)
    if flag == "strict_new_borrower_universe":
        base = [
            row for row in rows
            if row["source_is_new_fund"] == "True"
            and row["overlap_day4_borrower"] == "False"
            and row["overlap_day4_source_event_id"] == "False"
            and row["overlap_development_borrower"] == "False"
        ]
        exact_block_count = diagnostics.get("strict_new_borrower_exact_borrower_blocks", 0)
    else:
        base = [
            row for row in rows
            if (row["source_is_new_fund"] == "True" or row["target_is_new_fund"] == "True")
            and row["overlap_day4_source_event_id"] == "False"
        ]
        exact_block_count = diagnostics.get("new_fund_exact_borrower_blocks", 0)
    same = sum(row["manager_relationship"] == "same_manager" for row in base)
    cross = sum(row["manager_relationship"] == "cross_manager" for row in base)
    verified = sum(row["target_cutoff_basis"] == "verified_earliest_results_day3" for row in selected)
    proxy = len(selected) - verified
    return {
        "target_observations_cross_manager": len(selected),
        "source_event_clusters": len({row["source_event_cluster_id"] for row in selected}),
        "unique_normalized_borrowers": len({row["normalized_borrower"] for row in selected}),
        "candidate_new_funds": len({
            str(cik)
            for row in selected
            for cik, is_new in (
                (row["source_cik"], row["source_is_new_fund"]),
                (row["target_cik"], row["target_is_new_fund"]),
            )
            if is_new == "True"
        }),
        "new_source_funds": len({row["source_cik"] for row in selected if row["source_is_new_fund"] == "True"}),
        "new_target_funds": len({row["target_cik"] for row in selected if row["target_is_new_fund"] == "True"}),
        "all_additional_fund_ciks_in_selected_relationships": sorted({
            str(cik)
            for row in selected
            for cik, is_new in (
                (row["source_cik"], row["source_is_new_fund"]),
                (row["target_cik"], row["target_is_new_fund"]),
            )
            if is_new == "True"
        }, key=int),
        "source_target_fund_pairs": len(pairs),
        "counts_by_period": dict(sorted(periods.items())),
        "counts_by_source": dict(sorted(source_funds.items())),
        "counts_by_target": dict(sorted(target_funds.items())),
        "reporting_window_days": {
            "p25": percentile(windows, 0.25),
            "median": statistics.median(windows) if windows else None,
            "p75": percentile(windows, 0.75),
            "min": min(windows) if windows else None,
            "max": max(windows) if windows else None,
        },
        "exact_borrower_block_target_relations_considered": exact_block_count,
        "surviving_exact_borrower_and_unique_facility_match": len(selected),
        "requiring_human_facility_review": len(selected),
        "target_cutoff_timing": {
            "verified_earliest_results": verified,
            "periodic_filing_proxy_pending_review": proxy,
        },
        "manager_relationship_before_cross_manager_primary_filter": {
            "same_manager": same,
            "cross_manager": cross,
            "total": same + cross,
        },
    }


def validate_output(rows: list[dict[str, object]]) -> None:
    if set(OUTPUT_FIELDS) & FORBIDDEN_OUTPUT_COLUMNS:
        raise RuntimeError("Forbidden numeric outcome column in Day 5 output schema")
    if len(rows) != len({row["candidate_observation_id"] for row in rows}):
        raise RuntimeError("Duplicate candidate observation IDs")
    if any(row["period_end"] == DEVELOPMENT_PERIOD for row in rows):
        raise RuntimeError("Development-contaminated 2025Q3 entered the candidate output")
    if any(row["strict_new_borrower_universe"] == "True" and row["overlap_day4_borrower"] == "True" for row in rows):
        raise RuntimeError("Day 4 borrower entered strict replication universe")
    if any(row["strict_new_borrower_universe"] == "True" and row["overlap_development_borrower"] == "True" for row in rows):
        raise RuntimeError("Development borrower entered strict replication universe")
    if any(row["strict_new_borrower_universe"] == "True" and row["source_is_new_fund"] != "True" for row in rows):
        raise RuntimeError("Existing source fund entered strict new-fund replication")
    if any(row["overlap_day4_source_event_id"] == "True" and row["new_fund_universe"] == "True" for row in rows):
        raise RuntimeError("Day 4 source event entered new-fund replication universe")


def build_summary(
    rows: list[dict[str, object]],
    diagnostics: dict,
    metadata: dict[str, dict[str, str]],
    existing_ciks: set[str],
    periods_by_cik: dict[str, set[str]],
    inputs: dict[str, Path],
) -> dict:
    strict = summarize_rows(rows, "strict_new_borrower_universe", diagnostics)
    new_fund = summarize_rows(rows, "new_fund_universe", diagnostics)
    additional_with_data = {
        cik for cik, periods in periods_by_cik.items()
        if cik not in existing_ciks and len(periods & STANDARD_PERIODS) >= 2
    }
    available_periods = sorted({period for periods in periods_by_cik.values() for period in periods})
    strict_target = (
        strict["unique_normalized_borrowers"] >= 50
        and strict["source_event_clusters"] >= 80
    )
    return {
        "status": "outcome_blind_replication_feasibility_only",
        "day4_result_status_carried_forward_without_reinterpretation": "exploratory_inconclusive",
        "locked_hypothesis": {
            "movement_definition": "abs(source_current_mark - source_prior_mark) >= 0.005",
            "B0": "target_prior_mark",
            "ShadowNAV": "target_prior_mark + (source_current_mark - source_prior_mark)",
            "independent_event_unit": "unique source economic-facility movement event",
            "multiple_targets": "average inside source_event_cluster_id before primary test",
            "permutation": "borrower-clustered sign-flip; 100000 draws; seed 20260814; add-one correction",
            "bootstrap": "borrower-cluster bootstrap; 10000 draws; seed 20260814",
            "day4_six_decision_criteria_unchanged": True,
            "optimized_reporting_window_filter_added": False,
        },
        "universe_definitions": {
            "strict_new_borrower": (
                "new source fund; borrower absent from Day 2/Day 3 development and Day 4; "
                "source event absent from Day 4; proxy cross-manager only"
            ),
            "new_fund": (
                "at least one fund outside the Day 4 19-fund universe; Day 4 source events excluded; "
                "previously seen borrowers allowed; proxy cross-manager only"
            ),
            "manager_status": (
                "Day 4 funds use the official map; added funds use deterministic filer-name family "
                "proxies and require canonical manager verification before freezing"
            ),
        },
        "fund_screen": {
            "day4_funds": len(existing_ciks),
            "additional_funds_with_at_least_two_standard_periods": len(additional_with_data),
            "additional_listed_fund_proxies": sum(
                cik not in existing_ciks and meta["listed_status"] == "listed"
                for cik, meta in metadata.items()
            ),
            "additional_funds_in_any_candidate_relationship": len({
                str(cik)
                for row in rows
                for cik, is_new in (
                    (row["source_cik"], row["source_is_new_fund"]),
                    (row["target_cik"], row["target_is_new_fund"]),
                )
                if is_new == "True"
            }),
        },
        "period_availability": {
            "requested_primary": [quarter_label(value) for value in sorted(PRIMARY_PERIODS)],
            "aggregate_cache_standard_periods": [quarter_label(value) for value in available_periods],
            "development_2025Q3_excluded": True,
            "later_untouched_quarters_available_in_existing_cache": [],
        },
        "strict_new_borrower": strict,
        "new_fund": new_fund,
        "overlap_audit": {
            "day4_borrower_rows_all_candidates": sum(row["overlap_day4_borrower"] == "True" for row in rows),
            "day4_borrower_rows_strict": sum(
                row["strict_new_borrower_universe"] == "True" and row["overlap_day4_borrower"] == "True"
                for row in rows
            ),
            "day4_source_event_rows_all_candidates": sum(row["overlap_day4_source_event_id"] == "True" for row in rows),
            "day4_source_event_rows_new_fund": sum(
                row["new_fund_universe"] == "True" and row["overlap_day4_source_event_id"] == "True"
                for row in rows
            ),
            "development_borrower_rows_all_candidates": sum(row["overlap_development_borrower"] == "True" for row in rows),
            "development_borrower_rows_strict": sum(
                row["strict_new_borrower_universe"] == "True" and row["overlap_development_borrower"] == "True"
                for row in rows
            ),
        },
        "duplicate_vote_audit": {
            "duplicate_identities": diagnostics.get("duplicate_vote_identities", 0),
            "duplicate_rows": diagnostics.get("duplicate_vote_rows", 0),
            "status": "clear" if diagnostics.get("duplicate_vote_identities", 0) == 0 else "requires_deduplication_before_freeze",
        },
        "planning_target": {
            "unique_borrowers": 50,
            "independent_source_event_clusters": 80,
            "appears_feasible_before_human_review": strict_target,
            "not_a_pass_criterion": True,
            "caveat": (
                "Counts are pre-review maxima. Facility identity, added-fund manager family, listed-target "
                "status, and proxy reporting cutoffs must be verified without outcomes before any freeze."
            ),
        },
        "diagnostics": diagnostics,
        "prohibitions": {
            "target_same_period_numeric_fields_joined": False,
            "target_numeric_outcomes_materialized": False,
            "predictions_materialized": False,
            "errors_calculated": False,
            "replication_result_calculated": False,
            "inferential_statistics_calculated": False,
            "confirmatory_decision_assigned": False,
            "sample_frozen": False,
            "result_tag_created": False,
        },
        "input_sha256": {name: sha256_file(path) for name, path in inputs.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--facilities",
        type=Path,
        default=Path("/private/tmp/finance-day3-sec-cache/bdc_facilities_all_agg.csv"),
    )
    parser.add_argument(
        "--universe-estimate", type=Path, default=Path("data/day3/universe_expansion_estimate.csv")
    )
    parser.add_argument(
        "--manager-map", type=Path, default=Path("data/day3/bdc_manager_map.csv")
    )
    parser.add_argument(
        "--reporting-order", type=Path, default=Path("data/day3/reporting_order_extended.csv")
    )
    parser.add_argument(
        "--day4-sample", type=Path, default=Path("data/day4/confirmatory_included_sample.csv")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/day5/replication_universe_candidates.csv")
    )
    parser.add_argument(
        "--summary", type=Path, default=Path("data/day5/replication_feasibility_summary.json")
    )
    args = parser.parse_args()

    inputs = {
        "economic_facility_v2_all_funds_cache": args.facilities,
        "day3_universe_expansion_estimate": args.universe_estimate,
        "day3_manager_map": args.manager_map,
        "day3_reporting_order_extended": args.reporting_order,
        "day4_frozen_included_sample": args.day4_sample,
    }
    for path in inputs.values():
        if not path.exists():
            raise FileNotFoundError(path)

    metadata, existing_ciks = load_fund_metadata(args.universe_estimate, args.manager_map)
    day4_borrowers, day4_clusters, development_borrowers = load_exclusions(args.day4_sample)
    facilities, period_acceptances, periods_by_cik = load_facilities(args.facilities, metadata)
    verified_cutoffs = load_verified_cutoffs(args.reporting_order)
    rows, diagnostics = build_candidates(
        facilities,
        metadata,
        existing_ciks,
        period_acceptances,
        verified_cutoffs,
        day4_borrowers,
        day4_clusters,
        development_borrowers,
    )
    validate_output(rows)
    write_csv(args.output, rows)
    summary = build_summary(
        rows,
        diagnostics,
        metadata,
        existing_ciks,
        periods_by_cik,
        inputs,
    )
    summary["candidate_file_sha256"] = sha256_file(args.output)
    summary["candidate_rows_all_relationships"] = len(rows)
    write_json(args.summary, summary)
    print(json.dumps({
        "candidate_rows": len(rows),
        "strict": {
            key: summary["strict_new_borrower"][key]
            for key in ("target_observations_cross_manager", "source_event_clusters", "unique_normalized_borrowers")
        },
        "new_fund": {
            key: summary["new_fund"][key]
            for key in ("target_observations_cross_manager", "source_event_clusters", "unique_normalized_borrowers")
        },
        "planning_target_appears_feasible": summary["planning_target"]["appears_feasible_before_human_review"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
